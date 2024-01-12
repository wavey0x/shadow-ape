import json
from typing import List, Optional

from ape import chain, config, networks, accounts, project
from ape_foundry.provider import FoundryForkConfig
from ape_solidity import compiler
from ethpm_types import ContractType
from rich import print
from hexbytes import HexBytes

VAULT_ADDRESS = '0x06bDF212C290473dCACea9793890C5024c7Eb02c'
PRISMA_CORE = '0x5d17eA085F2FF5da3e6979D5d26F1dBaB664ccf8'
TOKEN = '0xdA47862a83dac0c112BA89c6abC2159b95afd71C'
VOTER = '0xfd8DF0Db401Ab7EC7a06a8465134FA32132e850C'
LOCKER = '0x3f78544364c3eCcDCe4d9C89a630AEa26122829d'
STABILITY_POOL = '0xed8B26D99834540C5013701bB3715faFD39993Ba'
MANAGER = '0xD0eFDF01DD8d650bBA8992E2c42D0bC6d441a673'

def main():
    block_number = 18589327
    tx = '0xb46d28236606ea70d8b02e00309a398a07e7bc7f2be2e6267fcb733dab090279'
    receipt = chain.provider.get_receipt(tx)
    timestamp = chain.blocks[block_number].timestamp
    block_transactions = chain.blocks[block_number].transactions
    tx_index = next(i for i, x in enumerate(block_transactions) if x.txn_hash.hex() == tx)

    # fork at a previous block
    # config._plugin_configs["foundry"].port = 7545

    block_number = 18589327 

    config._plugin_configs["foundry"].fork = {
        "ethereum": {
            "mainnet-fork": FoundryForkConfig(
                upstream_provider = "geth",
                block_number = block_number - 1,
            )
        }
    }

    # with networks.ethereum.mainnet_fork.use_provider("foundry", provider_settings=config.get_config('foundry').dict()):
    with networks.fork(provider_name="foundry", provider_settings={'block_number': block_number}):
        print('block number', chain.blocks.height)


        # Deploy
        replacement_contract = accounts.test_accounts[0].deploy(
            project.PrismaVault, 
            PRISMA_CORE, 
            TOKEN, 
            LOCKER, 
            VOTER, 
            STABILITY_POOL, 
            MANAGER
        )
        chain.provider._make_request(
            "anvil_setCode", [VAULT_ADDRESS, replacement_contract.code]
        )

        chain.provider._make_request("evm_setAutomine", [False])
        chain.provider._make_request('anvil_setNextBlockBaseFeePerGas',[0])

        replay_tx = block_transactions[tx_index]
        replay_tx.gas_limit += 100_000
        replay_tx.chain_id = chain.chain_id  # ape bug?
        chain.provider.unlock_account(replay_tx.sender)
        user = accounts[replay_tx.sender]
        print("nonce", user.nonce)
        replay_tx = replay_tx.dict()
        del replay_tx['type']
        replay_tx['nonce'] = replay_tx['nonce'] + 2
        replay_tx_hash = chain.provider.web3.eth.send_transaction(replay_tx)

        # advance one block and make sure we at the original height and timestamp
        chain.mine()

        fork_receipt = chain.provider.web3.eth.get_transaction_receipt(replay_tx_hash)
        fork_logs = fork_receipt["logs"]
        assert fork_receipt["status"], "tx failed"

        contract_logs = [log for log in fork_logs if log["address"] == VAULT_ADDRESS]

        # logs = replacement_contract.BoostConsumed.range(block_number-1, block_number)
        
        events = chain.provider.network.ecosystem.decode_logs(
            contract_logs, replacement_contract.BoostConsumed.abi
        )
        print(list(events))
        print(list(contract_logs))
        # for e in events:
        #     print(e)
        assert False
        for report, version in zip(reports, versions):
            contract_logs = [log for log in fork_logs if log["address"] == report.contract_address]
            event = next(
                chain.provider.network.ecosystem.decode_logs(
                    contracts[version].events["Fees"], contract_logs
                )
            )
            # offset the remaining logs so we don't read the same log twice
            fork_logs = [log for log in fork_logs if log["logIndex"] > event.log_index]
            results.append(Fees.parse_obj(event.event_arguments))

    return results

def boost_consumed(tx):
    logs = []
    receipt = chain.provider.get_transaction(tx)
    for event in vault_selectors("StrategyReported"):
        logs.extend(receipt.decode_logs(event))

    reports = sorted(logs, key=LOG_KEY)

    return reports

def vault_selectors(event_name):
    """
    Find all variants of an event selector across all vault versions.
    """
    each_version = [Contract(vaults[0]) for vaults in get_vaults_by_version().values()]

    return list(
        unique(
            (getattr(vault, event_name).abi for vault in each_version),
            key=lambda abi: abi.selector,
        )
    )