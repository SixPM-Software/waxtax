from typing import Literal

import requests

CLAIM_ACTIONS = ["claimdrop", "claimdropkey", "claimdropwl", "claimwproof"]


class FailedRequestException(Exception):
    """Called when API request fails"""

    def __init__(self, message: str = "Couldn't connect to WAX API"):
        self.message = message
        super().__init__(self.message)


class MissingTrxException(Exception):
    """Called when no matching transaction found"""

    def __init__(self, message: str = "Couldn't find this transaction"):
        self.message = message
        super().__init__(self.message)


def check_country_code(
    block_num: int,
    trx_id: str,
    endpoint: str,
) -> str:
    """_summary_

    Args:
        block_num (int): The block the transaction is in
        trx_id (str): The transaction ID
        endpoint (str): The history endpoint to use

    Raises:
        FailedRequestException: _description_
        MissingTrxException: _description_

    Returns:
        str: _description_
    """
    transaction = requests.get(
        f"{endpoint}/v2/history/get_transaction",
        params={"id": trx_id, "block_hint": block_num},
    )
    if transaction.status_code != 200:
        raise FailedRequestException

    data = transaction.json().get("actions")
    if not data:
        raise MissingTrxException

    country_code = "None"
    for action in data:
        if action["act"]["name"] in CLAIM_ACTIONS:
            country_code = action["act"]["data"].get("country")
        if not country_code:
            country_code = "None"
    return country_code


if __name__ == "__main__":
    # test case
    print(
        check_country_code(
            184126171,
            "bbc8c30af77d9d3904656cff6ff26cb17ed4b5c02b261b5dc38c9054e391f51a",
            "neftyblocksd",
            "https://hyperion.tokengamer.io",
        )
    )
