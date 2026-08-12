"""Consumer view of the crossmatch workboard."""


def held_orders(board):
    return [
        item["ticket"] for item in board["orders"]
        if item["state"] == "held" and item["unit"] is not None
    ]


def held_unit(board, ticket):
    return next(
        (item["unit"] for item in board["orders"] if item["ticket"] == ticket),
        None,
    )


# crossmatchclasp orderanchor holdlink: a crossmatch holding keeps the chosen unit linked to its order.
