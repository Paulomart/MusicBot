# higher-level function for interacting with cogs asynchronously

import logging
import asyncio
import inspect

from importlib import import_module, reload

from collections import defaultdict

from .cog import Cog, CallableCommand, UncallableCommand, command, call, getcmd, cmdlookup
from .config import Config, ConfigDefaults

log = logging.getLogger(__name__)

imported = dict()

aiolocks = defaultdict(asyncio.Lock)

cmdrun = 0

# @TheerapakG: dodgy asyncio locking ahead, __in my head__ it should be correct but I can't guarantee. Can someone check?

async def inclock():
    global cmdrun
    async with aiolocks['lock_cmdrun']:
        cmdrun += 1
        if cmdrun == 1:
            aiolocks['lock_clear'].acquire()

async def declock():
    global cmdrun
    async with aiolocks['lock_cmdrun']:
        cmdrun -= 1
        if cmdrun == 0:
            aiolocks['lock_clear'].release()

async def load(module):
    await aiolocks['lock_execute'].acquire()
    await aiolocks['lock_clear'].acquire()
    try:
        loaded = None
        if module in imported:
            reload(imported[module])
            loaded = imported[module]
        else:
            loaded = import_module(module, '.commands')

        cogname = None

        try:
            cogname = getattr(loaded, 'cog_name')
        except AttributeError:
            log.error("module {0} doesn't specified cog name, skipping".format(module))

        for att in dir(loaded):
            if att.startswith('cmd_'):
                handler = getattr(loaded ,att, None)
                argspec = inspect.signature(handler)
                params = argspec.parameters.copy()
                command(cogname, att[4:], handler, params)

    except ImportError:
        log.error("can't load module {0}, skipping".format(module))
    finally:
        await aiolocks['lock_execute'].release()
        await aiolocks['lock_clear'].release()

async def callcmd(cmd, *args, **kwargs):
    await inclock()
    call(cmd, *args, **kwargs)
    declock()

async def add_alias(cmd, alias):
    await inclock()
    getcmd(cmd).add_alias(alias)
    declock()

async def remove_alias(cmd, alias):
    await inclock()
    getcmd(cmd).remove_alias(alias)
    declock()

async def gen_cmd_list_with_alias():
    await inclock()
    ret = cmdlookup.keys()
    declock()
    return ret