from algopy import ARC4Contract, String
from algopy.arc4 import abimethod


class AlgoRacersRegistry(ARC4Contract):
    @abimethod()
    def hello(self, name: String) -> String:
        return "Hello, " + name

    @abimethod()
    def get_version(self) -> String:
        return String("AlgoRacers v2.0.0-algokit")
