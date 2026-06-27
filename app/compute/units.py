CONVERSIONS = {
    # length
    ("km", "miles"):   lambda v: v * 0.621371,
    ("miles", "km"):   lambda v: v * 1.60934,
    ("m", "ft"):       lambda v: v * 3.28084,
    ("ft", "m"):       lambda v: v * 0.3048,
    ("m", "cm"):       lambda v: v * 100,
    ("cm", "m"):       lambda v: v / 100,
    ("m", "mm"):       lambda v: v * 1000,
    ("mm", "m"):       lambda v: v / 1000,
    ("inches", "cm"):  lambda v: v * 2.54,
    ("cm", "inches"):  lambda v: v / 2.54,
    # weight
    ("kg", "lbs"):     lambda v: v * 2.20462,
    ("lbs", "kg"):     lambda v: v / 2.20462,
    ("kg", "g"):       lambda v: v * 1000,
    ("g", "kg"):       lambda v: v / 1000,
    ("g", "mg"):       lambda v: v * 1000,
    ("mg", "g"):       lambda v: v / 1000,
    # temperature
    ("c", "f"):        lambda v: v * 9/5 + 32,
    ("f", "c"):        lambda v: (v - 32) * 5/9,
    ("c", "k"):        lambda v: v + 273.15,
    ("k", "c"):        lambda v: v - 273.15,
    # speed
    ("kmh", "mph"):    lambda v: v * 0.621371,
    ("mph", "kmh"):    lambda v: v * 1.60934,
    ("ms", "kmh"):     lambda v: v * 3.6,
    ("kmh", "ms"):     lambda v: v / 3.6,
    # energy
    ("j", "cal"):      lambda v: v / 4.184,
    ("cal", "j"):      lambda v: v * 4.184,
    ("kj", "kcal"):    lambda v: v / 4.184,
    ("kcal", "kj"):    lambda v: v * 4.184,
    # pressure
    ("pa", "atm"):     lambda v: v / 101325,
    ("atm", "pa"):     lambda v: v * 101325,
    ("bar", "pa"):     lambda v: v * 100000,
    ("pa", "bar"):     lambda v: v / 100000,
}


def convert_units(value: float, from_unit: str, to_unit: str) -> str:
    key = (from_unit.lower(), to_unit.lower())
    if key in CONVERSIONS:
        result = CONVERSIONS[key](value)
        if result == int(result):
            return f"{value} {from_unit} = {int(result)} {to_unit}"
        return f"{value} {from_unit} = {result:.4g} {to_unit}"
    return f"I don't know how to convert {from_unit} to {to_unit} yet."