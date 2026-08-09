"""Calendar interval overlap rules."""


def intervals_overlap(left_start, left_end, right_start, right_end):
    return left_start < right_end and right_start < left_end


def room_is_free(bookings, request):
    return not any(
        booking.room == request.room
        and intervals_overlap(
            booking.start_minute,
            booking.end_minute,
            request.start_minute,
            request.end_minute,
        )
        for booking in bookings
    )
