#!/usr/bin/env python

import optparse

from twisted.internet import defer
from twisted.python.failure import Failure

__doc__ = """\
usage: %prog
A Deferred simulator. Use this to see how a particular
set of callbacks and errbacks will fire in a deferred.\
"""

class BadInput(Exception): pass


def parse_args():
    parser = optparse.OptionParser(usage=__doc__)

    options, args = parser.parse_args()

    if args:
        parser.error('No arguments supported.')


class Screen(object):
    """An ascii screen."""

    def __init__(self):
        self.pixels = {} # (x, y) -> char

    def draw_char(self, x, y, char):
        self.pixels[x,y] = char

    def draw_horiz_line(self, x, y, width):
        for i in range(width):
            self.draw_char(x + i, y, '-')

    def draw_vert_line(self, x, y, height, end_arrow=False):
        for i in range(height):
            self.draw_char(x, y + i, '|')
        if end_arrow:
            self.draw_char(x - 1, y + height - 1, '\\')
            self.draw_char(x + 1, y + height - 1, '/')

    def draw_text(self, x, y, text):
        for i, char in enumerate(text):
            self.draw_char(x + i, y, char)

    def __str__(self):
        width = max([p[0] + 1 for p in self.pixels] + [0])
        height = max([p[1] + 1 for p in self.pixels] + [0])

        s = ''

        for y in range(height):
            for x in range(width):
                s += self.pixels.get((x,y), ' ')
            s += '\n'

        return s
        

class Callback(object):
    """
    A widget representing a single callback or errback.

    Each callback widget has one of three styles:

      return - a callback that returns a given value
      fail - a callback that raises an Exception(value)
      passthru - a callback that returns its argument unchanged

    The widget is also a callable that behaves according
    to the widget's style.
    """

    height = 5

    def __init__(self, style, value=None):
        self.style = style
        self.value = value
        self.min_width = len(repr(self)) + 4

    def __call__(self, res):
        if self.style == 'return':
            return self.value
        if self.style == 'fail':
            raise Exception(self.value)
        return res

    def __repr__(self):
        if self.style == 'passthru':
            return 'passthru'
        return self.style + ' ' + self.value

    def draw(self, screen, x, y, width):
        screen.draw_horiz_line(x, y, width)
        screen.draw_horiz_line(x, y + 4, width)
        screen.draw_vert_line(x, y + 1, 3)
        screen.draw_vert_line(x + width - 1, y + 1, 3)
        screen.draw_text(x + 1, y + 2, repr(self).center(width - 2))


class Deferred(object):
    """An widget for a deferred."""

    def __init__(self, pairs):
        assert pairs
        self.pairs = pairs
        self.callback_width = max([p[0].min_width for p in self.pairs] + [0])
        self.callback_width = max([p[1].min_width for p in self.pairs]
                                  + [self.callback_width])
        self.width = self.callback_width * 2 + 2
        self.height = Callback.height * len(self.pairs)
        self.height += 3 * len(self.pairs[1:])

    def draw(self, screen, x, y):
        for callback, errback in self.pairs:
            callback.draw(screen, x, y, self.callback_width)
            errback.draw(screen, x + self.callback_width + 2,
                         y, self.callback_width)
            y += Callback.height + 3


class FiredDeferred(object):
    """A widget for a fired deferred."""

    def __init__(self, deferred, method):
        self.deferred = deferred
        self.method = method
        self.height = deferred.height + 10
        self.width = deferred.width

    def draw(self, screen, x, y, result):
        d = self.make_drawing_deferred(screen, x, y)

        if self.method == 'callback':
            d.callback(result)
        else:
            d.errback(Exception(result))

    def make_drawing_deferred(self, screen, x, y):
        callback_width = self.deferred.callback_width

        callback_mid_x = x - 1 + callback_width / 2

        errback_left_x = x + callback_width + 2
        errback_mid_x = errback_left_x - 1 + callback_width / 2

        class DrawState(object):
            last_x = None
            last_y = None

        state = DrawState()

        def draw_connection(x):
            if state.last_x == x:
                screen.draw_vert_line(x - 1 + callback_width / 2,
                                      state.last_y - 3, 3, True)
                return

            if state.last_x < x:
                screen.draw_vert_line(callback_mid_x, state.last_y - 3, 2)
                screen.draw_vert_line(errback_mid_x,
                                      state.last_y - 2, 2, True)
            else:
                screen.draw_vert_line(errback_mid_x, state.last_y - 3, 2)
                screen.draw_vert_line(callback_mid_x,
                                      state.last_y - 2, 2, True)

            screen.draw_horiz_line(callback_mid_x + 1,
                                   state.last_y - 2,
                                   errback_mid_x - callback_mid_x - 1)

        def wrap_callback(cb, x):
            def callback(res):
                cb.draw(screen, x, state.last_y, callback_width)
                draw_connection(x)
                state.last_x = x
                state.last_y += cb.height + 3
                return cb(res)
            return callback

        def draw_value(res, y):
            if isinstance(res, Failure):
                text = 'Exception(%s)' % (res.value.args[0],)
                text = text.center(callback_width + 20)
                screen.draw_text(errback_left_x - 10, y, text)
            else:
                screen.draw_text(x, y, res.center(callback_width))

        def draw_start(res):
            draw_value(res, y)
            if isinstance(res, Failure):
                state.last_x = errback_left_x
            else:
                state.last_x = x
            state.last_y = y + 4
            return res

        def draw_end(res):
            draw_value(res, state.last_y)
            if isinstance(res, Failure):
                draw_connection(errback_left_x)
            else:
                draw_connection(x)

        d = defer.Deferred()

        d.addBoth(draw_start)

        for pair in self.deferred.pairs:
            callback = wrap_callback(pair[0], x)
            errback = wrap_callback(pair[1], errback_left_x)
            d.addCallbacks(callback, errback)

        d.addBoth(draw_end)

        return d


def get_next_pair():
    """Get the next callback/errback pair from the user."""

    def get_cb():
        if not parts:
            raise BadInput('missing command')

        cmd = parts.pop(0).lower()

        for command in ('return', 'fail', 'passthru'):
            if command.startswith(cmd):
                cmd = command
                break
        else:
            raise BadInput('bad command: %s' % cmd)

        if cmd in ('return', 'fail'):
            if not parts:
                raise BadInput('missing argument')
            return Callback(cmd, parts.pop(0))
        else:
            return Callback(cmd)

    line = raw_input()

    if not line:
        return None

    parts = line.strip().split()

    callback, errback = get_cb(), get_cb()

    if parts:
        raise BadInput('extra arguments')

    return callback, errback


def get_pairs():
    """
    Get the list of callback/errback pairs from the user.
    They are returned as Callback widgets.
    """

    print """\
Enter a callback/errback pairs in the form:

  CALLBACK ERRBACK

Where CALLBACK and ERRBACK are one of:

  return VALUE
  fail VALUE
  passthru

And where VALUE is a string of only letters and numbers (no spaces).

You can abbreviate return/failure/passthru as r/f/p.

Examples:

  r awesome f terrible  # callback returns 'awesome'
                        # and errback raises Exception('terrible')

  f googly p # callback raises Exception('googly')
             # and errback passes it's failure along

Enter a blank line when you are done.
"""

    pairs = []

    while True:
        try:
            pair = get_next_pair()
        except BadInput, e:
            print 'ERROR:', e
            continue

        if pair is None:
            if not pairs:
                print 'You must enter at least one pair.'
                continue
            else:
                break

        pairs.append(pair)
           
    return pairs


def main():
    parse_args()

    d = Deferred(get_pairs())
    callback = FiredDeferred(d, 'callback')
    errback = FiredDeferred(d, 'errback')

    screen = Screen()

    callback.draw(screen, 0, 0, 'initial')
    errback.draw(screen, d.width + 12, 0, 'initial')

    print screen


if __name__ == '__main__':
    main()