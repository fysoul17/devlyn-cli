from intake.return_intake import new_record, record_return


def smoke():
    return record_return(new_record(), True, True)
