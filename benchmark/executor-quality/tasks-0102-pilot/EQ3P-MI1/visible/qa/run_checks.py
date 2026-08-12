import pathlib
import sys


sys.path.insert(0, str(pathlib.Path(__file__).parents[1]))
from intake.return_intake import new_record, record_return


def smoke():
    return record_return(new_record(), True, True)
