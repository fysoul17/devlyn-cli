"""An invoice: a list of lines, each an integer-cent amount, and their total."""

from billing.money import format_cents


class Invoice:
    """Lines are (description, amount_cents) pairs; amount_cents is always an int."""

    def __init__(self, customer):
        self.customer = customer
        self.lines = []

    def add_line(self, description, amount_cents):
        """Append a line. `amount_cents` must be an int number of cents."""
        if not isinstance(amount_cents, int):
            raise TypeError("amount_cents must be an int number of cents")
        self.lines.append((description, amount_cents))
        return self

    def total_cents(self):
        """Return the invoice total as an int number of cents."""
        return sum(amount for _, amount in self.lines)

    def render(self):
        """Return a plain-text invoice."""
        rows = [
            "%-28s %10s" % (description, format_cents(amount))
            for description, amount in self.lines
        ]
        rows.append("%-28s %10s" % ("TOTAL", format_cents(self.total_cents())))
        return "\n".join(rows) + "\n"
