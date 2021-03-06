import sys
import importlib
import pkgutil
import itertools
from io import StringIO
import signal
from argparse import ArgumentParser, RawDescriptionHelpFormatter

from kgtk import cli
from kgtk.exceptions import kgtk_exception_handler
from kgtk import __version__


# module name should NOT start with '__' (double underscore)
handlers = [x.name for x in pkgutil.iter_modules(cli.__path__)
                   if not x.name.startswith('__')]


pipe_delimiter = '/'

signal.signal(signal.SIGPIPE, signal.SIG_DFL)


class KGTKArgumentParser(ArgumentParser):
    def __init__(self, *args, **kwargs):
        if not kwargs.get('formatter_class'):
            kwargs['formatter_class'] = RawDescriptionHelpFormatter

        super(KGTKArgumentParser, self).__init__(*args, **kwargs)


def cli_entry(*args):
    """
    Usage:
        kgtk <command> [options]
    """
    parser = KGTKArgumentParser()
    parser.add_argument(
        '-V', '--version',
        action='version',
        version='KGTK %s' % __version__,
        help="show KGTK version number and exit."
    )

    sub_parsers = parser.add_subparsers(
        metavar='command',
        dest='cmd'
    )
    sub_parsers.required = True

    # load parser of each module
    # TODO: need to optimize with lazy loading method
    for h in handlers:
        mod = importlib.import_module('.{}'.format(h), 'kgtk.cli')
        sub_parser = sub_parsers.add_parser(h, **mod.parser())
        mod.add_arguments(sub_parser)

    if not args:
        args = tuple(sys.argv)
    if len(args) == 1:
        args = args + ('-h',)
    args = args[1:]

    stdout_ = sys.stdout
    last_stdout = StringIO()
    ret_code = 0

    for cmd_args in [tuple(y) for x, y in itertools.groupby(args, lambda a: a == pipe_delimiter) if not x]:
        # parse command and options
        args = parser.parse_args(cmd_args)

        # load module
        func = None
        if args.cmd:
            mod = importlib.import_module('.{}'.format(args.cmd), 'kgtk.cli')
            func = mod.run
            kwargs = vars(args)
            del kwargs['cmd']

        # run module
        last_stdout.close(); last_stdout = StringIO()
        ret_code = kgtk_exception_handler(func, **kwargs)
        sys.stdin.close(); sys.stdin = StringIO(last_stdout.getvalue())

    stdout_.write(last_stdout.getvalue())
    last_stdout.close(); sys.stdin.close()

    return ret_code
