import logging
import algokit_utils

logger = logging.getLogger(__name__)


def deploy() -> None:
    from smart_contracts.artifacts.pokedex_registry.pokedex_registry_client import (
        PokedexRegistryFactory,
        HelloArgs,
    )

    algorand = algokit_utils.AlgorandClient.from_environment()
    deployer_ = algorand.account.from_environment("DEPLOYER")

    factory = algorand.client.get_typed_app_factory(
        PokedexRegistryFactory, default_sender=deployer_.address
    )

    app_client, result = factory.deploy(
        on_update=algokit_utils.OnUpdate.AppendApp,
        on_schema_break=algokit_utils.OnSchemaBreak.AppendApp,
    )

    if result.operation_performed in [
        algokit_utils.OperationPerformed.Create,
        algokit_utils.OperationPerformed.Replace,
    ]:
        algorand.send.payment(
            algokit_utils.PaymentParams(
                amount=algokit_utils.AlgoAmount(algo=1),
                sender=deployer_.address,
                receiver=app_client.app_address,
            )
        )

    # 1. Call get_version
    version_res = app_client.send.get_version()
    logger.info(
        f"✅ PokedexRegistry App ID {app_client.app_id} deployed! "
        f"get_version() returned: '{version_res.abi_return}'"
    )

    # 2. Call hello
    hello_res = app_client.send.hello(args=HelloArgs(name="Trainer"))
    logger.info(f"✅ hello('Trainer') returned: '{hello_res.abi_return}'")
