# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
_logger = logging.getLogger(__name__)

cyrillic = \
    u'''\u0410	\u0430	A			a		
\u0411	\u0431	B			b		
\u0412	\u0432	V			v		
\u0413	\u0433	G			g		
\u0414	\u0434	D			d		
\u0415	\u0435	E			e		
\u0416	\u0436	Z	H		z	h	
\u0417	\u0437	Z			z		
\u0418	\u0438	I			i		
\u0419	\u0439	Y			y		
\u041a	\u043a	K			k		
\u041b	\u043b	L			l		
\u041c	\u043c	M			m		
\u041d	\u043d	N			n		
\u041e	\u043e	O			o		
\u041f	\u043f	P			p		
\u0420	\u0440	R			r		
\u0421	\u0441	S			s		
\u0422	\u0442	T			t		
\u0423	\u0443	U			u		
\u0424	\u0444	F			f		
\u0425	\u0445	H			h		
\u0426	\u0446	T	S		t	s	
\u0427	\u0447	C	H		c	h	
\u0428	\u0448	S	H		s	h	
\u0429	\u0449	S	H	T	s	h	t
\u042a	\u044a	A			a		
\u042c	\u044c	Y			y		
\u042e	\u044e	Y	U		y	u	
\u042f	\u044f	Y	A		y	a	'''

cyrillic = [line.split('\t') for line in cyrillic.split('\n')]
iso9, _iso9 = {}, cyrillic

for cyrmaj, cyrmin, latmaj1, latmaj2, latmaj3, latmin1, latmin2, latmin3 in _iso9:
    iso9[cyrmaj] = ''.join([latmaj1, latmaj2, latmaj3])
    iso9[cyrmin] = ''.join([latmin1, latmin2, latmin3])


def transliterate(source):
    result = []
    if not source:
        return ''
    l = len(source)
    forward = False
    for i, char in enumerate(source):
        if forward:
            forward = False
            continue
        if i + 1 == l and source[i:i + 1] == 'ия':
            result += ['i', 'a']
            forward = True
            continue
        elif i + 1 <= l:
            if source[i:i + 1] == 'дж':
                result += ['d', 'z', 'h']
                forward = True
                continue
            elif source[i:i + 1] == 'дз':
                result += ['d', 'z']
                forward = True
                continue
            elif source[i:i + 1] == 'ьо':
                result += ['y', 'o']
                forward = True
                continue
            elif source[i:i + 1] == 'йо':
                result += ['y', 'o']
                forward = True
                continue
        try:
            result.append(iso9[char])
        except KeyError:
            result.append(char)
    return ''.join(result)
