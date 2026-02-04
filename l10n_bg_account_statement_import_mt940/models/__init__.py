import re
import mt940.tags

mt940.tags.StatementNumber.pattern = """
    (?P<statement_number>\d+)
    (?:/?(?P<sequence_number>\d{1,6})|
    -(?P<alt_sequence_number>\d{1,6}))?
    $"""


class Tag(object):
    def parse(self, transactions, value):
        match = re.match(self.pattern, value, self.RE_FLAGS)
        if match:  # pragma: no branch
            self.logger.debug(
                'matched (%d) %r against "%s", got: %s',
                len(value), value, self.pattern,
                match.groupdict()
            )
        else:  # pragma: no cover
            self.logger.error(
                'matching id=%s (len=%d) "%s" against\n    %s',
                self.id,
                len(value),
                value,
                self.pattern
            )

            part_value = value
            for pattern in self.pattern.split('\n'):
                match = re.match(pattern, part_value, self.RE_FLAGS)
                if match:
                    self.logger.info(
                        'matched %r against %r, got: %s',
                        pattern, match.group(0),
                        match.groupdict()
                    )
                    part_value = part_value[len(match.group(0)):]
                else:
                    self.logger.error(
                        'no match for %r against %r',
                        pattern, part_value
                    )

            raise RuntimeError(
                'Unable to parse %r from %r' % (self, value),
                self, value
            )
        return match.groupdict()

mt940.tags.Tag.parse = Tag.parse

from . import account_journal
