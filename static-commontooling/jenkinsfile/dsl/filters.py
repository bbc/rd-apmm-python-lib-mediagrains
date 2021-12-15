# Copyright 2020 British Broadcasting Corporation
#
# This is an internal BBC tool and is not licensed externally
# If you have received a copy of this erroneously then you do
# not have permission to reproduce it.

from textx import metamodel_from_str


grammar = r"""
Stage:
    RestOfStringCmd | Make | RAMLTest | Wheel | Upload | RawStage;

RestOfStringCmd:
    cmd=RestOfStringCmdKeyword params=RESTOFSTRING;

RestOfStringCmdKeyword:
    '@setup' | '@agentsh' | '@sh' | '@fetchtags';

Make:
    cmd='@make' tgt=PARAM ctx=PARAM?;

RAMLTest:
    cmd='@ramltest';

Wheel:
    cmd='@wheel' tgt=PARAM?;

Upload:
    cmd='@upload' subcmd=UploadSubcommand;

UploadSubcommand:
    DocsRecursive | Docs | Artifactory | SimpleUploadSubcommand | Docker;

Docker:
    cmd='docker' params=RESTOFSTRING;

Docs:
    cmd='docs' params=RESTOFSTRING;

DocsRecursive:
    cmd='docs-recursive' params=RESTOFSTRING;

Artifactory:
    cmd='artifactory' dir=PARAM?;

SimpleUploadSubcommand:
    cmd=SimpleUploadSubcommandKeyword;

SimpleUploadSubcommandKeyword:
    'pypi' | 'snapshotmanifest';

RawStage:
    cmd=/(?s)[^@].*/;


RESTOFSTRING:
    /(?s).*/;

PARAM:
    /\S+/;
"""

mm = metamodel_from_str(grammar)


def parse_jcdsl(stage):
    return mm.model_from_str(stage)


def parse_jcdsl_list(stages):
    return [parse_jcdsl(stage) for stage in stages]
