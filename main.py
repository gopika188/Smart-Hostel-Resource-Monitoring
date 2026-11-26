def calculate_slab_charge(units, slabs):
    """Calculate progressive charges across consumption slabs."""
    charge = 0.0
    previous_limit = 0.0

    for upper_limit, rate in slabs:
        if units > previous_limit:
            slab_units = min(units, upper_limit) - previous_limit
            charge += slab_units * rate
            previous_limit = upper_limit
        else:
            break

    return round(charge, 2)


def evaluate_room(room, config):
    """Calculate electricity and water charges, check thresholds, and flag violations."""
    floor = int(room["floor"])
    room_no = room["room_no"]
    occupants = max(1, int(room.get("occupants", 1)))
    kwh_used = max(0.0, float(room["kwh_used"]))
    kl_used = max(0.0, float(room["kl_used"]))

    elec_charge = calculate_slab_charge(kwh_used, config["electricity_slabs"])
    water_charge = calculate_slab_charge(kl_used, config["water_slabs"])
    fixed_charge = round(config["room_fixed_charge"], 2)

    # Room-level and per-occupant thresholds
    max_room_kwh = config["max_kwh_per_occupant"] * occupants
    max_room_kl = config["max_kl_per_occupant"] * occupants

    violations = []
    penalty = 0.0

    if kwh_used > max_room_kwh:
        excess_kwh = round(kwh_used - max_room_kwh, 2)
        kwh_pen = round(excess_kwh * config["kwh_penalty_rate"], 2)
        penalty += kwh_pen
        violations.append(f"Power +{excess_kwh} kWh")

    if kl_used > max_room_kl:
        excess_kl = round(kl_used - max_room_kl, 2)
        kl_pen = round(excess_kl * config["kl_penalty_rate"], 2)
        penalty += kl_pen
        violations.append(f"Water +{excess_kl} kL")

    total_charge = round(elec_charge + water_charge + fixed_charge + penalty, 2)

    return {
        "floor": floor,
        "room_no": room_no,
        "occupants": occupants,
        "kwh_used": round(kwh_used, 2),
        "max_kwh": round(max_room_kwh, 2),
        "kl_used": round(kl_used, 2),
        "max_kl": round(max_room_kl, 2),
        "elec_charge": elec_charge,
        "water_charge": water_charge,
        "fixed_charge": fixed_charge,
        "penalty": round(penalty, 2),
        "total_charge": total_charge,
        "violations": violations,
        "violation_text": ", ".join(violations) if violations else "None",
    }


def compare_floors(room_results):
    """Aggregate and compare electricity, water, costs, and violations by floor."""
    floors_map = {}

    for r in room_results:
        fl = r["floor"]
        if fl not in floors_map:
            floors_map[fl] = {
                "floor": fl,
                "rooms": 0,
                "occupants": 0,
                "total_kwh": 0.0,
                "total_kl": 0.0,
                "total_cost": 0.0,
                "violation_rooms": 0,
            }

        f_rec = floors_map[fl]
        f_rec["rooms"] += 1
        f_rec["occupants"] += r["occupants"]
        f_rec["total_kwh"] = round(f_rec["total_kwh"] + r["kwh_used"], 2)
        f_rec["total_kl"] = round(f_rec["total_kl"] + r["kl_used"], 2)
        f_rec["total_cost"] = round(f_rec["total_cost"] + r["total_charge"], 2)
        if r["violations"]:
            f_rec["violation_rooms"] += 1

    # Sort floors in ascending numerical order
    floor_keys = sorted(floors_map.keys())
    floor_list = [floors_map[k] for k in floor_keys]

    for f_rec in floor_list:
        occ = f_rec["occupants"] if f_rec["occupants"] > 0 else 1
        f_rec["kwh_per_student"] = round(f_rec["total_kwh"] / occ, 2)
        f_rec["kl_per_student"] = round(f_rec["total_kl"] / occ, 2)

    return floor_list


def print_hostel_report(room_results, floor_summary):
    """Print room-wise billing/violations and floor-by-floor comparison."""
    print("=" * 112)
    print("SMART HOSTEL RESOURCE MONITORING - ROOM-WISE REPORT")
    print("=" * 112)
    print(
        f"{'Flr':>3} {'Room':<7} {'Occ':>3} {'kWh(Lim)':>12} {'kL(Lim)':>11} "
        f"{'Elec(₹)':>8} {'Wat(₹)':>8} {'Pen(₹)':>7} {'Total(₹)':>9} {'Violations'}"
    )
    print("-" * 112)

    for r in room_results:
        kwh_col = f"{r['kwh_used']:.1f}({r['max_kwh']:.0f})"
        kl_col = f"{r['kl_used']:.1f}({r['max_kl']:.0f})"
        print(
            f"{r['floor']:>3} {r['room_no']:<7} {r['occupants']:>3} {kwh_col:>12} {kl_col:>11} "
            f"{r['elec_charge']:>8.2f} {r['water_charge']:>8.2f} {r['penalty']:>7.2f} "
            f"{r['total_charge']:>9.2f} {r['violation_text']}"
        )

    print("\n" + "=" * 112)
    print("FLOOR-WISE UTILIZATION COMPARISON")
    print("=" * 112)
    print(
        f"{'Floor':>5} {'Rooms':>6} {'Students':>8} {'Total kWh':>10} {'kWh/Stud':>9} "
        f"{'Total kL':>9} {'kL/Stud':>8} {'ViolRms':>8} {'Cost(₹)':>10}"
    )
    print("-" * 112)

    highest_kwh_floor = None
    highest_kl_floor = None

    for f in floor_summary:
        print(
            f"{f['floor']:>5} {f['rooms']:>6} {f['occupants']:>8} {f['total_kwh']:>10.2f} "
            f"{f['kwh_per_student']:>9.2f} {f['total_kl']:>9.2f} {f['kl_per_student']:>8.2f} "
            f"{f['violation_rooms']:>8} {f['total_cost']:>10.2f}"
        )
        if highest_kwh_floor is None or f["kwh_per_student"] > highest_kwh_floor["kwh_per_student"]:
            highest_kwh_floor = f
        if highest_kl_floor is None or f["kl_per_student"] > highest_kl_floor["kl_per_student"]:
            highest_kl_floor = f

    print("-" * 112)
    if highest_kwh_floor:
        print(
            f"Highest Per-Student Power Usage : Floor {highest_kwh_floor['floor']} "
            f"({highest_kwh_floor['kwh_per_student']:.2f} kWh/student)"
        )
    if highest_kl_floor:
        print(
            f"Highest Per-Student Water Usage : Floor {highest_kl_floor['floor']} "
            f"({highest_kl_floor['kl_per_student']:.2f} kL/student)"
        )
    print("=" * 112 + "\n")


def main():
    hostel_config = {
        "electricity_slabs": [
            (100.0, 5.0),           # First 100 kWh @ ₹5.00/kWh
            (250.0, 6.5),           # 100 - 250 kWh @ ₹6.50/kWh
            (float("inf"), 8.0),    # Above 250 kWh @ ₹8.00/kWh
        ],
        "water_slabs": [
            (10.0, 12.0),           # First 10 kL @ ₹12.00/kL
            (25.0, 20.0),           # 10 - 25 kL @ ₹20.00/kL
            (float("inf"), 35.0),   # Above 25 kL @ ₹35.00/kL
        ],
        "room_fixed_charge": 150.0,
        "max_kwh_per_occupant": 90.0,
        "max_kl_per_occupant": 6.0,
        "kwh_penalty_rate": 3.0,
        "kl_penalty_rate": 15.0,
    }

    rooms_data = [
        {"floor": 1, "room_no": "F1-101", "occupants": 2, "kwh_used": 145.0, "kl_used": 9.5},
        {"floor": 1, "room_no": "F1-102", "occupants": 3, "kwh_used": 295.0, "kl_used": 17.0},
        {"floor": 2, "room_no": "F2-201", "occupants": 2, "kwh_used": 210.0, "kl_used": 15.5},
        {"floor": 2, "room_no": "F2-202", "occupants": 2, "kwh_used": 165.0, "kl_used": 11.0},
        {"floor": 3, "room_no": "F3-301", "occupants": 3, "kwh_used": 320.0, "kl_used": 23.0},
        {"floor": 3, "room_no": "F3-302", "occupants": 2, "kwh_used": 130.0, "kl_used": 8.0},
    ]

    room_results = [evaluate_room(rm, hostel_config) for rm in rooms_data]
    floor_summary = compare_floors(room_results)
    print_hostel_report(room_results, floor_summary)


if __name__ == "__main__":
    main()
