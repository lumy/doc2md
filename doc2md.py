#! /usr/bin/env python
# encoding: utf-8
"""
Very lightweight docstring to Markdown converter.


### License

Copyright © 2013 Thomas Gläßle <t_glaessle@gmx.de>

This work  is free. You can  redistribute it and/or modify  it under the
terms of the Do What The Fuck  You Want To Public License, Version 2, as
published by Sam Hocevar. See the COPYING file for more details.

This program  is free software.  It comes  without any warranty,  to the
extent permitted by applicable law.


### Description

Little convenience tool to extract docstrings from a module or class and
convert them to GitHub Flavoured Markdown:

https://help.github.com/articles/github-flavored-markdown

Its purpose is to quickly generate `README.md` files for small projects.


### API

The interface consists of the following functions:

 - `doctrim(docstring)`
 - `doc2md(docstring, title)`

You can run this script from the command line like:

$ doc2md.py [-a] [--no-toc] [-t title] module-name [class-name] > README.md


### Limitations

At the moment  this is suited only  for a very specific use  case. It is
hardly forseeable, if I will decide to improve on it in the near future.

"""
import re
import sys
import inspect

__all__ = ['doctrim', 'doc2md']

doctrim = inspect.cleandoc

def unindent(lines):
    """
    Remove common indentation from string.

    Unlike doctrim there is no special treatment of the first line.

    """
    try:
        # Determine minimum indentation:
        indent = min(len(line) - len(line.lstrip())
                     for line in lines if line)
    except ValueError:
        return lines
    else:
        return [line[indent:] for line in lines]

def code_block(lines, language=''):
    """
    Mark the code segment for syntax highlighting.
    """
    return ['```' + language] + lines + ['```']

def doctest2md(lines):
    """
    Convert the given doctest to a syntax highlighted markdown segment.
    """
    is_only_code = True
    lines = unindent(lines)
    for line in lines:
        if not line.startswith('>>> ') and not line.startswith('... ') and line not in ['>>>', '...']:
            is_only_code = False
            break
    if is_only_code:
        orig = lines
        lines = []
        for line in orig:
            lines.append(line[4:])
    return lines

def doc_code_block(lines, language):
    if language == 'python':
        lines = doctest2md(lines)
    return code_block(lines, language)

_reg_section = re.compile('^#+ ')
def is_heading(line):
    return _reg_section.match(line)

def get_heading(line):
    assert is_heading(line)
    part = line.partition(' ')
    return len(part[0]), part[2]

def make_heading(level, title):
    return '#'*max(level, 1) + ' ' + title

def find_sections(lines):
    """
    Find all section names and return a list with their names.
    """
    sections = []
    for line in lines:
        if is_heading(line):
            if not line.startswith("##"):
                raise Exception("Shouldn't be a bigger header")
            sections.append(get_heading(line))
    return sections

def make_toc(sections):
    """
    Generate table of contents for array of section names.
    """
    if not sections:
        return []
    outer = min(n for n,t in sections)
    refs = []
    for ind,sec in sections:
        ref = sec.lower()
        ref = ref.replace(' ', '-')
        ref = ref.replace('?', '')
        refs.append("    "*(ind-outer) + "- [%s](#%s)" % (sec, ref))
    return refs

type_url = [
  ("bool", "[bool](https://docs.python.org/2/library/stdtypes.html#boolean-values)"),
  ("str", "[str](https://docs.python.org/2/library/stdtypes.html#sequence-types-str-unicode-list-tuple-bytearray-buffer-xrange)"),
  ("int", "[int](https://docs.python.org/2/library/stdtypes.html#numeric-types-int-float-long-complex)"),
  ("float", "[float](https://docs.python.org/2/library/stdtypes.html#numeric-types-int-float-long-complex)"),
  ("list", "[list](https://docs.python.org/2/tutorial/datastructures.html#more-on-lists)"),
  ("Exception", "[Exception](https://docs.python.org/2/tutorial/errors.html)"),
]

def _doc2md(lines, shiftlevel=0):
    md = []
    is_code = False
    for line in lines:
        trimmed = line.lstrip()
        if is_code:
            if line:
                code.append(line)
            else:
                is_code = False
                md += doc_code_block(code, language)
                md += [line]
        elif trimmed.startswith('>>> '):
            is_code = True
            language = 'python'
            code = [line]
        elif trimmed.startswith('$ '):
            is_code = True
            language = 'bash'
            code = [line]
        elif shiftlevel != 0 and is_heading(line):
            level, title = get_heading(line)
            md += [make_heading(level + shiftlevel, title)]
        elif trimmed.startswith(":param"):
            line = line.replace(":param", "-")
            for c_type, url in type_url:
              if c_type in line:
                line = line.replace(c_type, url)
            md += [line.lstrip()]
        elif trimmed.startswith(":throw"):
            line = line.replace(":throw", "- throw")
            for c_type, url in type_url:
              if c_type in line:
                line = line.replace(c_type, url)
            md += ["", line.lstrip()]
        elif trimmed.startswith(":return"):
            line = line.replace(":return", "- return")
            for c_type, url in type_url:
              if c_type in line:
                line = line.replace(c_type, url)
            md += ["", line.lstrip()]
        else:
            md += [line]
    if is_code:
        md += doc_code_block(code, language)
    return md + [""]

def doc2md(module, title, min_level=1, more_info=False, toc=True):
    """
    Convert a docstring to a markdown text.
    """
    docstr = module.__doc__
    if module.__doc__ is None:
      docstr = ""
    if inspect.isclass(module) and module.__init__.__doc__:
        t = module.__init__.__doc__
        docstr += "\n\n" + t + "\n\n"
    text = doctrim(docstr)
    lines = text.split('\n')
    sections = find_sections(lines)
    if sections:
        level = min(n for n,t in sections)
    else:
        level = min_level

    shiftlevel = 0
    if level < min_level:
        shiftlevel = min_level - level
        level = min_level
        sections = [(lev+shiftlevel, tit) for lev,tit in sections]

    if inspect.isfunction(module):
        t = inspect.getsource(module).split("\n")[0]
        i = 0 # Use when there is @ or other stuff on the top of the function
        while not t.lstrip().startswith("def"):
            t = inspect.getsource(module).split("\n")[i]
            i += 1
        title = t[t.find(title):t.find(":")]
    elif inspect.isclass(module):
        t = inspect.getsource(module.__init__).split("\n")[0]
        title = title + t[t.find("("):t.find(":")]
        level += 1
    elif inspect.ismethod(module):
        t = inspect.getsource(module).split("\n")[0]
        title = t[t.find(title):t.find(":")]
    else:
        raise Exception("Not Known type ? %s" % module)
    if title.startswith("_"):
        title = "\\" + title
    md = [ make_heading(level, title), ""]
    while len(lines) > 0 and not lines[0].lstrip().startswith(":"):
      md.append(lines.pop(0).lstrip())
    md.append("")
    if toc:
        md += make_toc(sections)
    md += _doc2md(lines, shiftlevel)
    if more_info:
        return (md, sections)
    else:
        return "\n".join(md)

def class2md(cls, title, min_level=1, more_info=False, toc=True):
    """
    Convert a class to a markdown text.
    """
    md, sec = doc2md(cls, title,
                     min_level=min_level, more_info=True, toc=False)
    for entry in sorted(inspect.getmembers(cls)):
      if entry[0].startswith("__") and entry[0].endswith("__"):
        continue
      c_md, c_sec = doc2md(entry[1], entry[0], min_level=min_level+2, more_info=True, toc=False)
      md += c_md + ["\n"]
      sec += c_sec
    return md, sec

def mod2md(module, title, toc=True):
    """
    Generate markdown document from module.
    """
    docstr = module.__doc__

    text = doctrim(docstr) if docstr is not None else ""
    lines = text.split('\n')

    sections = find_sections(lines)
    if sections:
        level = min(n for n,t in sections) - 1
    else:
        level = 1

    api_md = []
    api_sec = []
    class_md = []
    class_sec = []
    if module.__md__:

        sections.append((level+1, "API"))

        for name in module.__md__:
            entry = module.__dict__[name]
            if inspect.isclass(entry):
                md, sec = class2md(entry, name, min_level=level, more_info=True, toc=False)
                class_sec += sec
                class_md += md
            elif entry.__doc__:
                api_sec.append((level + 2, name))
                api_md += ['', '']
                md, sec = doc2md(entry, name,
                        min_level=level+2, more_info=True, toc=False)
                api_sec += sec
                api_md += md

    sections += api_sec

    # headline
    md = [
        make_heading(level, title),
        "",
        lines.pop(0),
        ""
    ]

    # main sections
    if toc:
        md += make_toc(sections)
    md += _doc2md(lines)

    # API section
    if len(class_md) > 0:
      md += [
        '',
        '',
        make_heading(level, "Class"),
      ]

      if toc:
          md += ['']
          md += make_toc(class_sec)
      md += class_md

    if len(api_md) > 0:
      md += [
        '',
        '',
        make_heading(level, "Functions"),
      ]

      if toc:
          md += ['']
          md += make_toc(api_sec)
      md += api_md


    return "\n".join(md)

def main(args=None):
    # parse the program arguments
    import argparse
    parser = argparse.ArgumentParser(
            description='Convert docstrings to markdown.')

    parser.add_argument(
            'module', help='The module containing the docstring.')
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
            'entry', nargs='?',
            help='Convert only docstring of this entry in module.')
    group.add_argument(
            '-a', '--all', dest='all', action='store_true',
            help='Create an API section with the contents of module.__all__.')
    parser.add_argument(
            '-t', '--title', dest='title',
            help='Document title (default is module name)')
    parser.add_argument(
            '--no-toc', dest='toc', action='store_false', default=True,
            help='Do not automatically generate the TOC')
    args = parser.parse_args(args)

    import importlib
    import inspect
    import os

    def add_path(*pathes):
        for path in reversed(pathes):
            if path not in sys.path:
                sys.path.insert(0, path)

    file = inspect.getfile(inspect.currentframe())
    add_path(os.path.realpath(os.path.abspath(os.path.dirname(file))))
    add_path(os.getcwd())

    mod_name = args.module
    if mod_name.endswith('.py'):
        mod_name = mod_name.rsplit('.py', 1)[0]
    title = args.title or mod_name.replace('_', '-')

    module = importlib.import_module(mod_name)

    if args.all:
        print(mod2md(module, title, toc=args.toc))

    else:
        if args.entry:
            docstr = module.__dict__[args.entry].__doc__
        else:
            docstr = module.__doc__

        print(doc2md(docstr, title, toc=args.toc))

if __name__ == "__main__":
    main()
