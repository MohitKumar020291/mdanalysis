# -*- Mode: python; tab-width: 4; indent-tabs-mode:nil; -*-
# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
#
# MDAnalysis --- http://mdanalysis.googlecode.com
# Copyright (c) 2006-2011 Naveen Michaud-Agrawal,
#               Elizabeth J. Denning, Oliver Beckstein,
#               and contributors (see website for details)
# Released under the GNU Public Licence, v2 or any higher version
#
# Please cite your use of MDAnalysis in published work:
#
#     N. Michaud-Agrawal, E. J. Denning, T. B. Woolf, and
#     O. Beckstein. MDAnalysis: A Toolkit for the Analysis of
#     Molecular Dynamics Simulations. J. Comput. Chem. (2011),
#     doi:10.1002/jcc.21787
#

"""
Helper functions --- :mod:`MDAnalysis.core.util`
====================================================

Small helper functions that don't fit anywhere else.

Files and directories
---------------------

.. autofunction:: filename
.. function:: openany(directory[,mode='r'])

   Context manager to open a compressed (bzip2, gzip) or plain file
   (uses :func:`anyopen`).

.. autofunction:: anyopen

.. autofunction:: greedy_splitext


Containers and lists
--------------------

.. autofunction:: iterable
.. autofunction:: asiterable


File parsing
------------

.. autoclass:: FORTRANReader
   :members:
.. autodata:: FORTRAN_format_regex


Data manipulation and handling
------------------------------

.. autofunction:: fixedwidth_bins

"""
from __future__ import with_statement

__docformat__ = "restructuredtext en"

import os.path
from contextlib import contextmanager
import bz2, gzip
import re

def filename(name,ext=None,keep=False):
    """Return a new name that has suffix attached; replaces other extensions.

    :Arguments:
      *name*
           filename; extension is replaced unless keep=True
      *ext*
           extension
      *keep*
           ``False``: replace existing extension; ``True``: keep if exists
    """
    name = str(name)
    if ext is None:
        return name
    if not ext.startswith(os.path.extsep):
        ext = os.path.extsep + ext
    #if name.find(ext) > 0:    # normally >= 0 but if we start with '.' then we keep it
    #    return name
    root, origext = os.path.splitext(name)
    if len(origext) == 0 or not keep:
        return root + ext
    return name

@contextmanager
def openany(datasource, mode='r'):
    """Open the datasource and close it when the context exits."""
    stream, filename = anyopen(datasource, mode=mode)
    try:
        yield stream
    finally:
        stream.close()

def anyopen(datasource, mode='r'):
    """Open datasource (gzipped, bzipped, uncompressed) and return a stream.

    :Arguments:
     *datasource*
        a file or a stream
     *mode*
        'r' or 'w'
    """
    # TODO: - make this act as ContextManager (and not return filename)
    #       - need to add binary 'b' to mode for compressed files?

    handlers = {'bz2': bz2.BZ2File, 'gz': gzip.open, '': file}

    if mode.startswith('r'):
        if hasattr(datasource,'next') or hasattr(datasource,'readline'):
            stream = datasource
            filename = '(%s)' % stream.name  # maybe that does not always work?
        else:
            stream = None
            filename = datasource
            for ext in ('bz2', 'gz', ''):   # file == '' should be last
                openfunc = handlers[ext]
                stream = _get_stream(datasource, openfunc, mode=mode)
                if not stream is None:
                    break
            if stream is None:
                raise IOError("Cannot open %(filename)r in mode=%(mode)r." % vars())
    elif mode.startswith('w'):
        if hasattr(datasource, 'write'):
            stream = datasource
            filename = '(%s)' % stream.name  # maybe that does not always work?
        else:
            stream = None
            filename = datasource
            name, ext = os.path.splitext(filename)
            if ext.startswith('.'):
                ext = ext[1:]
            if not ext in ('bz2', 'gz'):
                ext = ''   # anything else but bz2 or gz is just a normal file
            openfunc = handlers[ext]
            stream = openfunc(datasource, mode=mode)
            if stream is None:
                raise IOError("Cannot open %(filename)r in mode=%(mode)r with type %(ext)r." % vars())
    else:
        raise NotImplementedError("Sorry, mode=%(mode)r is not implemented for %(datasource)r" % vars())

    return stream, filename

def _get_stream(filename, openfunction=file, mode='r'):
    try:
        stream = openfunction(filename, mode=mode)
    except IOError:
        return None

    try:
        stream.readline()
        stream.close()
        stream = openfunction(filename,'r')
    except IOError:
        stream.close()
        stream = None
    return stream

def greedy_splitext(p):
    """Split extension in path *p* at the left-most separator."""
    path, root = os.path.split(p)
    extension = ''
    while True:
        root, ext = os.path.splitext(root)
        extension = ext + extension
        if not ext:
            break
    return root, extension

def iterable(obj):
    """Returns ``True`` if *obj* can be iterated over and is *not* a  string."""
    if type(obj) is str:
        return False    # avoid iterating over characters of a string

    if hasattr(obj, 'next'):
        return True    # any iterator will do
    try:
        len(obj)       # anything else that might work
    except TypeError:
        return False
    return True

def asiterable(obj):
    """Returns obj so that it can be iterated over; a string is *not* treated as iterable"""
    if not iterable(obj):
        obj = [obj]
    return obj

#: Regular expresssion (see :mod:`re`) to parse a simple `FORTRAN edit descriptor`_.
#:   ``(?P<repeat>\d?)(?P<format>[IFELAX])(?P<numfmt>(?P<length>\d+)(\.(?P<decimals>\d+))?)?``
#: .. _FORTRAN edit descriptor: http://www.cs.mtu.edu/~shene/COURSES/cs201/NOTES/chap05/format.html
FORTRAN_format_regex = "(?P<repeat>\d+?)(?P<format>[IFEAX])(?P<numfmt>(?P<length>\d+)(\.(?P<decimals>\d+))?)?"
_FORTRAN_format_pattern = re.compile(FORTRAN_format_regex)

def strip(s):
    """Convert *s* to a string and return it white-space stripped."""
    return str(s).strip()

class FixedcolumnEntry(object):
    """Represent an entry at specific fixed columns.

    Reads from line[start:stop] and converts according to
    typespecifier.
    """
    convertors = {'I': int, 'F': float, 'E': float, 'A': strip}
    def __init__(self, start, stop, typespecifier):
        """
        :Arguments:
         *start*
            first column
         *stop*
            last column + 1
         *typespecifier*
            'I': int, 'F': float, 'E': float, 'A': stripped string

        The start/stop arguments follow standard Python convention in that
        they are 0-based and that the *stop* argument is not included.
        """
        self.start = start
        self.stop = stop
        self.typespecifier = typespecifier
        self.convertor = self.convertors[typespecifier]
    def read(self, line):
        """Read the entry from *line* and convert to appropriate type."""
        try:
            return self.convertor(line[self.start:self.stop])
        except ValueError:
            raise ValueError("%r: Failed to read&convert %r",
                             self, line[self.start:self.stop])
    def __len__(self):
        """Length of the field in columns (stop - start)"""
        return self.stop - self.start
    def __repr__(self):
        return "FixedcolumnEntry(%d,%d,%r)" % (self.start, self.stop, self.typespecifier)

class FORTRANReader(object):
    """FORTRANReader provides a method to parse FORTRAN formatted lines in a file.

    Usage::

       atomformat = FORTRANReader('2I10,2X,A8,2X,A8,3F20.10,2X,A8,2X,A8,F20.10')
       for line in open('coordinates.crd'):
           serial,TotRes,resName,name,x,y,z,chainID,resSeq,tempFactor = atomformat.read(line)

    Fortran format edit descriptors; see `Fortran Formats`_ for the syntax.

    Only simple one-character specifiers supported here: *I F E A X* (see
    :data:`FORTRAN_format_regex`).

    Strings are stripped of leading and trailing white space.

    .. _`Fortran Formats`: http://www.webcitation.org/5xbaWMV2x
    .. _`Fortran Formats (URL)`:
       http://www.cs.mtu.edu/~shene/COURSES/cs201/NOTES/chap05/format.html
    """

    def __init__(self, fmt):
        """Set up the reader with the FORTRAN format string.

        The string *fmt* should look like '2I10,2X,A8,2X,A8,3F20.10,2X,A8,2X,A8,F20.10'.
        """
        self.fmt = fmt.split(',')
        descriptors = [self.parse_FORTRAN_format(descriptor) for descriptor in self.fmt]
        start = 0
        self.entries = []
        for d in descriptors:
            if d['format'] != 'X':
                for x in range(d['repeat']):
                    stop = start + d['length']
                    self.entries.append(FixedcolumnEntry(start,stop,d['format']))
                    start = stop
            else:
                start += d['totallength']

    def read(self, line):
        """Parse *line* according to the format string and return list of values.

        Values are converted to Python types according to the format specifier.

        :Returns: list of entries with appropriate types
        :Raises: :exc:`ValueError` if any of the conversions cannot be made
                 (e.g. space for an int)

        .. SeeAlso:: :meth:`FORTRANReader.number_of_matches`
        """
        return [e.read(line) for e in self.entries]

    def number_of_matches(self, line):
        """Return how many format entries could be populated with legal values."""
        # not optimal, I suppose...
        matches = 0
        for e in self.entries:
            try:
                e.read(line)
                matches += 1
            except ValueError:
                pass
        return matches

    def parse_FORTRAN_format(self, edit_descriptor):
        """Parse the descriptor.

          parse_FORTRAN_format(edit_descriptor) --> dict

        :Returns: dict with totallength (in chars), repeat, length,
                  format, decimals; if the specifier could not be parsed,
                  an empty dict is returned.
        :Raises: :exc:`ValueError` if the *edit_descriptor* is not recognized.

        .. Note:: Specifiers: *L ES EN T TL TR / r S SP SS BN BZ* are *not*
           supported, and neither are the scientific notation *Ew.dEe* forms.
        """

        m = _FORTRAN_format_pattern.match(edit_descriptor.upper())
        if m is None:
            try:
                m = _FORTRAN_format_pattern.match("1"+edit_descriptor.upper())
            except:
                raise ValueError("unrecognized FORTRAN format %r" % edit_descriptor)
        d = m.groupdict()
        if d['repeat'] == '':
            d['repeat'] = 1
        if d['format'] == 'X':
            d['length'] = 1
        for k in ('repeat','length','decimals'):
            try:
                d[k] = int(d[k])
            except ValueError:   # catches ''
                d[k] = 0
            except TypeError:    # keep None
                pass
        d['totallength'] = d['repeat'] * d['length']
        return d

    def __len__(self):
        """Returns number of entries."""
        return len(self.entries)

    def __repr__(self):
        return self.__class__.__name__+"("+",".join(self.fmt)+")"

def fixedwidth_bins(delta,xmin,xmax):
    """Return bins of width delta that cover xmin,xmax (or a larger range).

    dict = fixedwidth_bins(delta,xmin,xmax)

    The dict contains 'Nbins', 'delta', 'min', and 'max'.
    """
    import numpy
    if not numpy.all(xmin < xmax):
        raise ValueError('Boundaries are not sane: should be xmin < xmax.')
    _delta = numpy.asarray(delta,dtype=numpy.float_)
    _xmin = numpy.asarray(xmin,dtype=numpy.float_)
    _xmax = numpy.asarray(xmax,dtype=numpy.float_)
    _length = _xmax - _xmin
    N = numpy.ceil(_length/_delta).astype(numpy.int_)      # number of bins
    dx = 0.5 * (N*_delta - _length)   # add half of the excess to each end
    return {'Nbins':N, 'delta':_delta,'min':_xmin-dx, 'max':_xmax+dx}

