# -*- coding: utf-8 -*-
"""
    pygments.formatters.latex
    ~~~~~~~~~~~~~~~~~~~~~~~~~

    Formatter for LaTeX fancyvrb output.

    :copyright: 2006 by Georg Brandl.
    :license: BSD, see LICENSE for more details.
"""
import cStringIO

from pygments.formatter import Formatter
from pygments.token import Token
from pygments.util import get_bool_opt, get_int_opt


__all__ = ['LatexFormatter']


def escape_tex(text):
    return text.replace('@', '\x00').    \
                replace('[', '\x01').    \
                replace(']', '\x02').    \
                replace('\x00', '@at[]').\
                replace('\x01', '@lb[]').\
                replace('\x02', '@rb[]')


DOC_TEMPLATE = r'''
\documentclass{%(docclass)s}
\usepackage{fancyvrb}
\usepackage{color}
\usepackage[%(encoding)s]{inputenc}
%(preamble)s

%(styledefs)s

\begin{document}

\section*{%(title)s}

%(code)s
\end{document}
'''


class LatexFormatter(Formatter):
    r"""
    Format tokens as LaTeX code. This needs the `fancyvrb` and `color`
    standard packages.

    Without the `full` option, code is formatted as one ``Verbatim``
    environment, like this:

    .. sourcecode:: latex

        \begin{Verbatim}[commandchars=@\[\]]
        @Can[def ]@Cax[foo](bar):
            @Can[pass]
        \end{Verbatim}

    The command sequences used here (``@Can`` etc.) are generated from the given
    `style` and can be retrieved using the `get_style_defs` method.

    With the `full` option, a complete LaTeX document is output, including
    the command definitions in the preamble.

    The `get_style_defs(arg='')` method of a `LatexFormatter` returns a string
    containing ``\newcommand`` commands defining the commands used inside the
    ``Verbatim`` environments. If the argument `arg` is true,
    ``\renewcommand`` is used instead.

    Additional options accepted:

    `docclass`
        If the `full` option is enabled, this is the document class to use
        (default: ``'article'``).

    `preamble`
        If the `full` option is enabled, this can be further preamble commands,
        e.g. ``\usepackage`` (default: ``''``).

    `verboptions`
        Additional options given to the Verbatim environment (see the *fancyvrb*
        docs for possible values) (default: ``''``).

    """

    def __init__(self, **options):
        Formatter.__init__(self, **options)
        self.docclass = options.get('docclass', 'article')
        self.preamble = options.get('preamble', '')
        self.linenos = get_bool_opt(options, 'linenos', False)
        self.linenostart = abs(get_int_opt(options, 'linenostart', 1))
        self.linenostep = abs(get_int_opt(options, 'linenostep', 1))
        self.verboptions = options.get('verboptions', '')
        self.nobackground = get_bool_opt(options, 'nobackground', False)

        self._create_stylecmds()


    def _create_stylecmds(self):
        t2c = self.ttype2cmd = {Token: ''}
        c2d = self.cmd2def = {}

        letters = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
        first = iter(letters)
        second = iter(letters)
        firstl = first.next()

        def rgbcolor(col):
            if col:
                return ','.join(['%.2f' %(int(col[i] + col[i + 1], 16) / 255.0)
                                 for i in (0, 2, 4)])
            else:
                return '1,1,1'

        for ttype, ndef in self.style:
            cmndef = '#1'
            if ndef['bold']:
                cmndef = r'\textbf{' + cmndef + '}'
            if ndef['italic']:
                cmndef = r'\textit{' + cmndef + '}'
            if ndef['underline']:
                cmndef = r'\underline{' + cmndef + '}'
            if ndef['color']:
                cmndef = r'\textcolor[rgb]{%s}{%s}' % (
                    rgbcolor(ndef['color']),
                    cmndef
                )
            if ndef['border']:
                cmndef = r'\fcolorbox[rgb]{%s}{%s}{%s}' % (
                    rgbcolor(ndef['border']),
                    rgbcolor(ndef['bgcolor']),
                    cmndef
                )
            elif ndef['bgcolor']:
                cmndef = r'\colorbox[rgb]{%s}{%s}' % (
                    rgbcolor(ndef['bgcolor']),
                    cmndef
                )
            if cmndef == '#1':
                continue
            try:
                alias = 'C' + firstl + second.next()
            except StopIteration:
                firstl = first.next()
                second = iter(letters)
                alias = 'C' + firstl + second.next()
            t2c[ttype] = alias
            c2d[alias] = cmndef

    def get_style_defs(self, arg=''):
        """
        Return the \\newcommand sequences needed to define the commands
        used to format text in the verbatim environment. If ``arg`` is
        given and true, use \\renewcommand instead.
        """
        nc = (arg and r'\renewcommand' or r'\newcommand')
        return '%s\\at{@}\n%s\\lb{[}\n%s\\rb{]}\n' % (nc, nc, nc) + \
               '\n'.join(['%s\\%s[1]{%s}' % (nc, alias, cmndef)
                          for alias, cmndef in self.cmd2def.iteritems()
                          if cmndef != '#1'])

    def format(self, tokensource, outfile):
        # TODO: add support for background colors
        enc = self.encoding

        if self.full:
            realoutfile = outfile
            outfile = cStringIO.StringIO()

        outfile.write(r'\begin{Verbatim}[commandchars=@\[\]')
        if self.linenos:
            start, step = self.linenostart, self.linenostep
            outfile.write(',numbers=left' +
                          (start and ',firstnumber=%d' % start or '') +
                          (step and ',stepnumber=%d' % step or ''))
        if self.verboptions:
            outfile.write(',' + self.verboptions)
        outfile.write(']\n')

        for ttype, value in tokensource:
            if enc:
                value = value.encode(enc)
            value = escape_tex(value)
            cmd = self.ttype2cmd.get(ttype)
            while cmd is None:
                ttype = ttype.parent
                cmd = self.ttype2cmd.get(ttype)
            if cmd:
                spl = value.split('\n')
                for line in spl[:-1]:
                    if line:
                        outfile.write("@%s[%s]" % (cmd, line))
                    outfile.write('\n')
                if spl[-1]:
                    outfile.write("@%s[%s]" % (cmd, spl[-1]))
            else:
                outfile.write(value)

        outfile.write('\n\\end{Verbatim}\n')

        if self.full:
            realoutfile.write(DOC_TEMPLATE %
                dict(docclass  = self.docclass,
                     preamble  = self.preamble,
                     title     = self.title,
                     encoding  = self.encoding,
                     styledefs = self.get_style_defs(),
                     code      = outfile.getvalue()))
