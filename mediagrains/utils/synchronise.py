# Copyright 2019 British Broadcasting Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""\
Some utility functions for running synchronous and asynchronous code together.
"""

from typing import TypeVar, Optional, Awaitable, Any, Generic
import asyncio
import threading
from inspect import iscoroutinefunction, isawaitable, isasyncgenfunction

T = TypeVar('T')


def run_awaitable_synchronously(f: Awaitable[T]) -> Optional[T]:
    """Runs an awaitable coroutine object as a synchronous call.

    Works from code running in a run-loop.
    Works from code running outside a run-loop.
    Works when there is a runloop already for this thread, but this code is not called from it.
    """
    class ResultsType:
        def __init__(self):
            self.rval: Optional[T] = None
            self.exception: Optional[Exception] = None

    results = ResultsType()

    async def _capture_results_async(a: Awaitable[T], results: ResultsType) -> None:
        try:
            rval = await a
        except Exception as e:
            results.exception = e
        else:
            results.rval = rval

    def _restore_results(results: ResultsType) -> Optional[T]:
        if results.exception is not None:
            raise results.exception
        else:
            return results.rval

    def _run_awaitable_in_existing_run_loop(a: Awaitable[T], loop: asyncio.AbstractEventLoop) -> Optional[T]:
        loop.run_until_complete(_capture_results_async(a, results))
        return _restore_results(results)

    def _run_awaitable_inside_new_runloop(a: Awaitable[T]) -> Optional[T]:
        loop = asyncio.new_event_loop()
        rval = _run_awaitable_in_existing_run_loop(a, loop)
        return rval

    def _run_awaitable_in_new_thread(a: Awaitable[T]) -> Optional[T]:
        def __inner() -> None:
            loop = asyncio.new_event_loop()
            loop.run_until_complete(_capture_results_async(a, results))
            loop.close()

        t = threading.Thread(target=__inner)
        t.start()
        t.join()

        return _restore_results(results)

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        # In Python 3.6 trying to get an event loop when none can be automatically created is a an exception
        return _run_awaitable_inside_new_runloop(f)
    else:
        if loop.is_running():
            # There is already a running loop on this thread so we need to spawn a new thread
            return _run_awaitable_in_new_thread(f)
        else:
            # We have An existing event loop, but it is not running, so we can run it.
            return _run_awaitable_in_existing_run_loop(f, loop)


def run_asyncgenerator_synchronously(gen):
    async def __get_next(gen):
        return await gen.__anext__()

    while True:
        try:
            yield run_awaitable_synchronously(__get_next(gen))
        except StopAsyncIteration:
            raise StopIteration


class Synchronised(Generic[T]):
    def __init__(self, other: T):
        self._other = other

    def __getattr__(self, name: str) -> Any:
        attr = getattr(self._other, name)
        if iscoroutinefunction(attr):
            return lambda *args, **kwargs: run_awaitable_synchronously(attr(*args, **kwargs))
        if isasyncgenfunction(attr):
            return lambda *args, **kwargs: run_asyncgenerator_synchronously(attr(*args, **kwargs))
        elif isawaitable(attr):
            return run_awaitable_synchronously(attr)
        else:
            return attr
