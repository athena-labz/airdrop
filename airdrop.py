"""Build a transaction using transaction builder"""

from blockfrost import ApiUrls
from typing import List

import pycardano as pyc
import json


def send_transaction(
    context: pyc.BlockFrostChainContext,
    skey: pyc.PaymentSigningKey,
    sender_address: pyc.Address,
    asset_policy_id: pyc.ScriptHash,
    asset_asset_name: pyc.AssetName,
    outputs: List[dict],
):
    builder = pyc.TransactionBuilder(context)
    builder.add_input_address(sender_address)
    print(sender_address)

    for output in outputs:
        asset = pyc.Asset()
        asset[asset_asset_name] = output["amount"]

        multi_asset = pyc.MultiAsset()
        multi_asset[asset_policy_id] = asset

        value = pyc.Value(2000000, multi_asset)
        transaction_output = pyc.TransactionOutput(output["address"], pyc.Value(2_000_000, multi_asset))
        
        lovelace = pyc.min_lovelace(context, output=transaction_output)
        value = pyc.Value(lovelace, multi_asset)

        builder.add_output(pyc.TransactionOutput(output["address"], value))

    # Create final signed transaction
    signed_tx = builder.build_and_sign([skey], change_address=sender_address)

    print(signed_tx)
    response = input("Are you sure you want to submit the transaction above (y/N) ?")
    if not response.lower() in ["y", "yes"]:
        print("Breaking, user cancelled transaction.")
        exit(1)

    # Submit signed transaction to the network
    context.submit_tx(signed_tx)

    print(f"Successfully submitted transaction {signed_tx.id}")


def read_config() -> dict:
    with open("config.json", "r") as config_file:
        config = json.load(config_file)

    return config


def main():
    config = read_config()

    if not "network" in config:
        print('Config file corrupted. No "network" key found')
        exit(1)

    if config["network"].lower() in ["testnet", "mainnet"]:
        response = input("Selected testnet. Confirm (y/N)? ")
        if not response.lower() in ["y", "yes"]:
            print("Breaking, wrong network selected.")
            exit(1)

        if config["network"].lower() == "testnet":
            network = pyc.Network.TESTNET
        else:
            network = pyc.Network.MAINNET

    if not "signing_key" in config:
        print('Config file corrupted. No "signing_key" key found')
        exit(1)

    psk = pyc.PaymentSigningKey.from_cbor(config["signing_key"])
    pvk = pyc.PaymentVerificationKey.from_signing_key(psk)

    if not "address" in config:
        print('Config file corrupted. No "address" key found')
        exit(1)

    sender_address = pyc.Address.from_primitive(config["address"])
    if sender_address.network != network:
        print(f"Address is from {sender_address.network} while current network is {network}")
        exit(1)

    if sender_address.payment_part != pvk.hash():
        print(
            "Signing key does not correspond to address. There is something wrong with either the signing key or the address. Contact Mateus."
        )
        exit(1)

    if not "blockfrost_project_id" in config:
        print('Config file corrupted. No "blockfrost_project_id" key found')
        exit(1)

    # Create a BlockFrost chain context
    context = pyc.BlockFrostChainContext(
        config["blockfrost_project_id"],
        base_url=ApiUrls.preprod.value
        if network == pyc.Network.TESTNET
        else ApiUrls.mainnet.value,
    )

    outputs = config["outputs"]
    new_outputs = []
    for output in outputs:
        if (not "address" in output) or (not isinstance(output["address"], str)):
            print('Config file corrupted. No "address" key (string) found inside one of outputs.')
            exit(1)

        if (not "amount" in output) or (not isinstance(output["amount"], int)):
            print('Config file corrupted. No "amount" key (int) found inside one of outputs.')
            exit(1)

        try:
            address = pyc.Address.from_primitive(output["address"])
        except Exception:
            print(f'Config file corrupted. Address {output['address']} is not a valid cardano address')
            exit(1)

        if address.network != network:
            print(f'Config file corrupted. Address {output['address']} is from network {address.network} while current network is {network}')
            exit(1)

        new_outputs.append({
            "address": address,
            "amount": output["amount"]
        })

    if not "asset" in config:
        print('Config file corrupted. No "asset" key found')
        exit(1)

    if not "policy_id" in config["asset"]:
        print('Config file corrupted. No "policy_id" key found in config asset')
        exit(1)

    try:
        policy_hash = pyc.ScriptHash.from_primitive(config["asset"]["policy_id"])
    except Exception as e:
        print(e)
        print('Config file corrupted. Failed to parse policy id.')
        exit(1)

    if not "asset_name" in config["asset"]:
        print('Config file corrupted. No "asset_name" key found in config asset')
        exit(1)

    try:
        asset_name = pyc.AssetName.from_primitive(config["asset"]["asset_name"])
    except Exception as e:
        print(e)
        print('Config file corrupted. Failed to parse asset name.')
        exit(1)

    send_transaction(context, psk, sender_address, policy_hash, asset_name, new_outputs)


if __name__ == "__main__":
    main()