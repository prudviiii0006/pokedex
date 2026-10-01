from algopy import ARC4Contract, String
from algopy.arc4 import abimethod


class PokedexRegistry(ARC4Contract):
    @abimethod()
    def hello(self, name: String) -> String:
        return "Hello, " + name

    @abimethod()
    def get_version(self) -> String:
        return String("Pokédex v2.0.0-algokit")
