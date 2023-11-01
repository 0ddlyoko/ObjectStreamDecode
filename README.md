# Python decoder of Java Serialize data

Maily used internally for reading Minecraft inventory data in Python.

## Usage

See `main.py` for example.

## Inspired by:
- [potats0/javaSerializationTools](https://github.com/potats0/javaSerializationTools/blob/eb0291bdd336e28ca5dd9ee86ba6d645f1bf6e8f/javaSerializationTools/ObjectRead.py)
- [knownsec/pocsuite3](https://github.com/knownsec/pocsuite3/blob/master/pocsuite3/lib/helper/java/serialization.py)

## Why making a new one?
- I want to learn how to decode Java Serialize data.
- I want to make a simple one.
- We can read data like int, long, float, double, ... easily without reading the block data using `set_block_data_mode(True)`.
