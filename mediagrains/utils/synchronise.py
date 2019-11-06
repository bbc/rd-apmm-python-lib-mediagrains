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

from typing import TypeVar, Optional, Awaitable, Any, Generic, AsyncIterator, Iterator, Tuple
import asyncio
import threading
from inspect import iscoroutinefunction, isawaitable, isasyncgenfunction

T = TypeVar('T')


class SynchronisationError(RuntimeError):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


def get_non_running_loop() -> Optional[asyncio.AbstractEventLoop]:
    """If there is an existing runloop on this thread and it isn't running return it.
    If there isn't one create one and return it.
    If there is an existing running loop on this thread then return None.
    """
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        # In Python 3.6 trying to get an event loop when none can be automatically created is a an exception
        return asyncio.new_event_loop()
    else:
        if loop.is_running():
            # There is already a running loop on this thread so we will need to spawn a new thread if we want to run one
            return None
        else:
            # We have An existing event loop, but it is not running, so we can run it.
            return loop


class ResultsType(Generic[T]):
    def __init__(self):
        self.rval: Optional[Tuple[T]] = None
        self.exception: Optional[Exception] = None

    async def capture(self, a: Awaitable[T]) -> None:
        try:
            rval = await a
        except Exception as e:
            self.exception = e
        else:
            self.rval = (rval,)

    def restore(self) -> T:
        if self.exception is not None:
            raise self.exception
        elif self.rval is None:
            raise SynchronisationError("Expected a result but none was produced")
        else:
            return self.rval[0]


def run_awaitable_synchronously(f: Awaitable[T]) -> T:
    """Runs an awaitable coroutine object as a synchronous call.

    Works from code running in a run-loop.
    Works from code running outside a run-loop.
    Works when there is a runloop already for this thread, but this code is not called from it.
    """
    results = ResultsType[T]()

    def _run_awaitable_in_existing_run_loop(a: Awaitable[T], loop: asyncio.AbstractEventLoop) -> T:
        loop.run_until_complete(results.capture(a))
        return results.restore()

    def _run_awaitable_in_new_thread(a: Awaitable[T]) -> T:
        def __inner() -> None:
            loop = asyncio.new_event_loop()
            loop.run_until_complete(results.capture(a))
            loop.close()

        t = threading.Thread(target=__inner)
        t.start()
        t.join()

        return results.restore()

    loop = get_non_running_loop()
    if loop is not None:
        return _run_awaitable_in_existing_run_loop(f, loop)
    else:
        return _run_awaitable_in_new_thread(f)


def run_asyncgenerator_synchronously(gen: AsyncIterator[T]) -> Iterator[T]:
    async def __get_next(gen):
        return await gen.__anext__()

    if get_non_running_loop() is not None:
        while True:
            try:
                yield run_awaitable_synchronously(__get_next(gen))
            except StopAsyncIteration:
                return
    else:
        results = ResultsType[T]()

        def _run_generator_in_new_thread(gen: AsyncIterator[T]) -> Tuple[threading.Thread, threading.Event, threading.Event]:
            agen_should_yield = threading.Event()
            agen_has_yielded = threading.Event()

            def __inner() -> None:
                async def _run_asyncgen_with_events(gen: AsyncIterator[T], agen_should_yield: threading.Event, agen_has_yielded: threading.Event) -> T:
                    try:
                        async for x in gen:
                            agen_should_yield.wait()
                            agen_should_yield.clear()
                            results.rval = (x,)
                            agen_has_yielded.set()

                        agen_should_yield.wait()
                        agen_should_yield.clear()
                        raise StopAsyncIteration
                    finally:
                        agen_has_yielded.set()

                loop = asyncio.new_event_loop()
                loop.run_until_complete(results.capture(_run_asyncgen_with_events(gen, agen_should_yield, agen_has_yielded)))
                loop.close()

            t = threading.Thread(target=__inner)
            t.daemon = True
            t.start()

            return (t, agen_should_yield, agen_has_yielded)

        (t, agen_should_yield, agen_has_yielded) = _run_generator_in_new_thread(gen)
        agen_should_yield.set()
        agen_has_yielded.wait()
        while t.is_alive():
            agen_has_yielded.clear()
            try:
                yield results.restore()
            except StopAsyncIteration:
                agen_should_yield.set()
                return
            agen_should_yield.set()
            agen_has_yielded.wait()


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
