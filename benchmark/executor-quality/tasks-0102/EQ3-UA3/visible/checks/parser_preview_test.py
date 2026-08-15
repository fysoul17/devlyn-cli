"""A quick operator check for declaration preview data."""


def preview_lists_valid_lines(preview):
    return len(preview["accepted_lines"]) >= 1


if __name__ == "__main__":
    print("Run the declaration checks through the fixture harness.")
