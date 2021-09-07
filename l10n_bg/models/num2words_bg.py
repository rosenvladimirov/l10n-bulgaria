# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import math

to_10_bg = (u'нула', u'един', u'два', u'три', u'четири', u'пет', u'шест',
            u'седем', u'осем', u'девет')
to_big_bg = (u'десет', u'сто', u'хиляд', u'милион', u'милард', u'трилион', u'квадрилион',
             u'квинтилион', u'секстилион', u'септилион', u'октилион', u'нонилион',
             u'децилион', u'децилиард', u'унвигинтилион', u'дуовигинтилион', 'тривигинтилион',
             u'тригинтилион')
exlusion_bg = (u'на', u'и', u'а', u' ', u'ста', u'стотин', u'една', u'две')
#                           0    ,      1   ,   2   , 3,     4 ,         5 ,                6 ,           7
units_names = (u'лев', u'лева', u'ст.')
syllable = exlusion_bg[3] + exlusion_bg[1] + exlusion_bg[3]


#          ' и '
# print syllable

def _convert_nn_bg(val, male=True, tausen=True):
    """ convert a value < 100 to Bulgarian
    """
    s = ''
    (mod, rem) = (val % 10, val // 10)
    # print val, ">", rem, mod, tausen
    if val == 10:
        return to_big_bg[0]
    if (rem == 0 and mod < 10):
        return tausen == False and exlusion_bg[7] or (mod == 1 and male != True) and exlusion_bg[6] or to_10_bg[
            int(mod)]
    if rem < 2:
        if mod == 1:
            return s.join((_convert_nn_bg(mod), exlusion_bg[2], to_big_bg[0]))
        return s.join((_convert_nn_bg(mod), exlusion_bg[0], to_big_bg[0]))
    elif (mod == 0):
        return s.join((_convert_nn_bg(rem), to_big_bg[0]))
    else:
        return s.join((_convert_nn_bg(rem, tausen=tausen), to_big_bg[0], syllable, _convert_nn_bg(mod, tausen=tausen)))


def _convert_nnn_bg(val, tausen=True):
    """ convert a value < 1000 to bulgarian
    """
    s = ''
    if val < 100:
        return _convert_nn_bg(val)
    (mod, rem) = (val % 100, val // 100)
    # print rem, mod
    if val == 100:
        return to_big_bg[1]
    if val == 200:
        return s.join((exlusion_bg[7], exlusion_bg[rem < 4 and 4 or 5]))
    if mod == 0:
        return s.join((_convert_nn_bg(rem, tausen=tausen), exlusion_bg[rem < 4 and 4 or 5]))
    else:
        return s.join(
            (_convert_nnn_bg(rem * 100), mod < 20 and syllable or exlusion_bg[3], _convert_nn_bg(mod, tausen=tausen)))


def _convert_nnnnnn_bg(val):
    """ convert a value < 1000000 to bulgarian
    """
    if val < 999:
        return _convert_nnn_bg(val)
    s = ''
    (mod, rem) = (val % 1000, val // 1000)
    # print val, ">>>>>", rem, mod
    if rem == 1:
        return s.join((to_big_bg[2], exlusion_bg[2], (mod > 20 and mod != 100) and exlusion_bg[3] or syllable,
                       _convert_nnn_bg(mod)))
    elif rem % 100 == 2:
        return s.join((exlusion_bg[7], exlusion_bg[3], to_big_bg[2], exlusion_bg[1],
                       (mod > 20 and mod != 100) and exlusion_bg[3] or syllable, _convert_nnn_bg(mod)))
    elif mod % 100 % 10 == 2:
        # print 'mod', 2
        return s.join((_convert_nnn_bg(rem, tausen=False), exlusion_bg[3], to_big_bg[2], exlusion_bg[1],
                       (mod > 20 and mod != 100) and exlusion_bg[3] or syllable, _convert_nnn_bg(mod)))
    else:
        return s.join((_convert_nnn_bg(rem), exlusion_bg[3], to_big_bg[2], exlusion_bg[1],
                       (mod > 20 and mod != 100) and exlusion_bg[3] or syllable, _convert_nnn_bg(mod)))


def _convert_big_bg(val):
    if val < 1000000:
        return _convert_nnnnnn_bg(val)
    else:
        s = ''
        inx = [i for i, j in enumerate(to_big_bg, 3) if val >= 1000 ** (i - 1) and val < 1000 ** (i - 0)][0]
        (mod, rem) = (val % 1000 ** (inx - 1), val // 1000 ** (inx - 1))
        # print val, "big", rem, mod
        return s.join((_convert_nnnnnn_bg(rem), exlusion_bg[3], to_big_bg[inx], rem > 1 and exlusion_bg[2] or u'',
                       exlusion_bg[3], _convert_big_bg(mod)))


def _int2word(val, big_val, currency_label=False):
    if currency_label:
        if big_val:
            big_units_names = currency_label
        else:
            big_units_names = (abs(val) == 1 and big_val) and currency_label or currency_label + u'a'
        nn_units_names = currency_label
    else:
        big_units_names = abs(val) == 1 and units_names[0] or units_names[1]
        nn_units_names = units_names[2]

    if val > 99:
        return [_convert_big_bg(abs(val)), exlusion_bg[3], big_units_names]
    elif 99 >= val >= 1:
        return [_convert_nn_bg(abs(val), False), exlusion_bg[3], big_units_names]
    else:
        return [_convert_nn_bg(abs(val), False), exlusion_bg[3], nn_units_names]


def _num2words(val, big_val=False, currency_label=False):
    if big_val:
        ret = big_val + ''.join([syllable] + _int2word(val, True, currency_label=currency_label))
        return ret[0].upper() + ret[1:]
    else:
        return ''.join(_int2word(val, False, currency_label=currency_label))


def num2words(val, currency_label=False):
    val_nn, big_val = math.modf(val)
    print(val_nn, big_val)
    ret = _num2words(int(big_val), currency_label=currency_label)
    if val_nn > 0:
        ret = _num2words(int(val_nn * 100), big_val=ret, currency_label=currency_label)
    return ret[0].upper() + ret[1:]
