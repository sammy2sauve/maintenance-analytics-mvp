"""
Unit tests for backend/adapter_faciliworks.py mapping functions.

No HTTP calls, no DB — pure function tests with static fixtures.

Run:
    pytest backend/tests/test_adapter_faciliworks.py -v
"""

import pytest
from backend.adapter_faciliworks import (
    _epoch_to_date,
    _map_status,
    _map_priority,
    _slug_from_name,
    build_asset_map,
    map_work_order,
)


# ── Static fixtures ───────────────────────────────────────────────────────────

ASSET_ACTIVE = {
    "equipmentMasterID": 1,
    "equipmentID": "MMC-CHIL-001",
    "description": "Centrifugal Chiller #1",
    "manufacturer": {"lookupValue": "Trane"},
    "modelNo": "CVHE500",
    "status": {"comboBoxText": "Active"},
}

ASSET_NO_EID = {
    "equipmentMasterID": 99,
    "equipmentID": "",
    "description": "Hot Water Pump #3",
    "manufacturer": {"lookupValue": "Armstrong"},
    "modelNo": "4300 Series",
    "status": {"comboBoxText": "Active"},
}

ASSET_LOWERCASE_EID = {
    "equipmentMasterID": 50,
    "equipmentID": "pump-001",          # not uppercase — should fall to slug
    "description": "Main Boiler Unit",
    "manufacturer": {"lookupValue": "Cleaver-Brooks"},
    "modelNo": "ClearFire-H",
    "status": {"comboBoxText": "Active"},
}

CM_COMPLETE = {
    "maintenanceKey": 1001,
    "woNumber": "CM-1001",
    "asset": {"equipmentMasterID": 1, "equipmentID": "MMC-CHIL-001"},
    "status": {"comboBoxText": "Complete"},
    "priority": {"comboBoxText": "High"},
    "createdDate": 1_700_000_000,   # 2023-11-14
    "dueDate":     1_700_500_000,   # ~5 days later
    "doneDate":    1_700_600_000,   # completed
    "startDate":   1_700_400_000,
    "estimatedHours": 3.0,
    "actualHours":    2.5,
    "description": "High head pressure alarm",
}

CM_OPEN_PAST_DUE = {
    "maintenanceKey": 1002,
    "woNumber": "CM-1002",
    "asset": {"equipmentMasterID": 1, "equipmentID": "MMC-CHIL-001"},
    "status": {"comboBoxText": "Open"},
    "priority": {"comboBoxText": "Medium"},
    "createdDate": 1_600_000_000,   # well in the past
    "dueDate":     1_600_500_000,   # also in the past
    "doneDate":    None,
    "startDate":   None,
    "estimatedHours": 2.0,
    "actualHours":    None,
    "description": "Refrigerant leak",
}

CM_NO_ASSET = {
    "maintenanceKey": 1003,
    "woNumber": "CM-1003",
    "asset": {"equipmentMasterID": 999, "equipmentID": "UNKNOWN-999"},
    "status": {"comboBoxText": "Open"},
    "priority": {"comboBoxText": "Low"},
    "createdDate": 1_700_000_000,
    "dueDate":     1_700_500_000,
    "doneDate":    None,
    "startDate":   None,
    "estimatedHours": 1.0,
    "actualHours":    None,
}

PM_COMPLETE = {
    "maintenanceKey": 5001,
    "woNumber": "PM-5001",
    "task": {"taskID": "PM-CHIL-MONTHLY"},
    "asset": {"equipmentMasterID": 1, "equipmentID": "MMC-CHIL-001"},
    "status": {"comboBoxText": "Complete"},
    "priority": {"comboBoxText": "Low"},
    "createdDate": 1_700_000_000,
    "dueDate":     1_700_500_000,
    "doneDate":    1_700_600_000,
    "startDate":   1_700_400_000,
    "estimatedHours": 3.0,
    "actualHours":    3.2,
    "description": "Chiller monthly inspection",
}

PM_OPEN = {
    "maintenanceKey": 5002,
    "woNumber": "PM-5002",
    "task": {"taskID": "PM-CTW-MONTHLY"},
    "asset": {"equipmentMasterID": 3, "equipmentID": "MMC-CTW-001"},
    "status": {"comboBoxText": "Open"},
    "priority": {"comboBoxText": "Low"},
    "createdDate": 1_700_000_000,
    "dueDate":     9_999_999_999,   # far future — not past due
    "doneDate":    None,
    "startDate":   None,
    "estimatedHours": 2.0,
    "actualHours":    None,
}


# ── _epoch_to_date ────────────────────────────────────────────────────────────

class TestEpochToDate:
    def test_known_timestamp(self):
        # 2023-11-14T22:13:20Z
        assert _epoch_to_date(1_700_000_000) == "2023-11-14"

    def test_none_returns_none(self):
        assert _epoch_to_date(None) is None

    def test_zero_returns_none(self):
        # Epoch 0 = 1970-01-01, but FaciliWorks uses 0 to mean "not set"
        # Adapter treats falsy values as None
        assert _epoch_to_date(0) is None

    def test_string_epoch(self):
        # API sometimes returns numeric strings
        assert _epoch_to_date("1700000000") == "2023-11-14"

    def test_returns_date_format(self):
        result = _epoch_to_date(1_710_000_000)
        assert len(result) == 10
        assert result[4] == "-" and result[7] == "-"


# ── _map_status ───────────────────────────────────────────────────────────────

class TestMapStatus:
    def test_complete(self):
        assert _map_status("Complete") == "Completed"

    def test_completed_variant(self):
        assert _map_status("Completed") == "Completed"

    def test_closed(self):
        assert _map_status("Closed") == "Completed"

    def test_cancelled(self):
        assert _map_status("Cancelled") == "Completed"

    def test_open(self):
        assert _map_status("Open") == "Open"

    def test_in_progress(self):
        assert _map_status("In Progress") == "Open"

    def test_on_hold(self):
        assert _map_status("On Hold") == "Open"

    def test_none_defaults_open(self):
        assert _map_status(None) == "Open"

    def test_case_insensitive(self):
        assert _map_status("COMPLETE") == "Completed"
        assert _map_status("complete") == "Completed"

    def test_unknown_defaults_open(self):
        assert _map_status("SomeWeirdStatus") == "Open"


# ── _map_priority ─────────────────────────────────────────────────────────────

class TestMapPriority:
    def test_high(self):
        assert _map_priority("High") == "High"

    def test_critical_maps_to_high(self):
        assert _map_priority("Critical") == "High"

    def test_medium(self):
        assert _map_priority("Medium") == "Medium"

    def test_normal_maps_to_medium(self):
        assert _map_priority("Normal") == "Medium"

    def test_low(self):
        assert _map_priority("Low") == "Low"

    def test_none_defaults_low(self):
        assert _map_priority(None) == "Low"

    def test_case_insensitive(self):
        assert _map_priority("HIGH") == "High"


# ── _slug_from_name ───────────────────────────────────────────────────────────

class TestSlugFromName:
    def test_pump(self):
        assert _slug_from_name("Main Water Pump 3") == "PUMP-003"

    def test_chiller(self):
        assert _slug_from_name("Centrifugal Chiller Unit 1") == "CHW-001"

    def test_boiler(self):
        assert _slug_from_name("Hot Water Boiler #2") == "BOIL-002"

    def test_ahu(self):
        assert _slug_from_name("Air Handling Unit 4") == "AHU-004"

    def test_vfd(self):
        assert _slug_from_name("VFD Drive 5") == "VFD-005"

    def test_fan(self):
        assert _slug_from_name("Exhaust Fan 2") == "FAN-002"

    def test_no_number_defaults_001(self):
        slug = _slug_from_name("Main Boiler Unit")
        assert slug.endswith("-001")

    def test_unknown_prefix(self):
        slug = _slug_from_name("Some Mystery Equipment 7")
        assert slug == "ASSET-007"


# ── build_asset_map ───────────────────────────────────────────────────────────

class TestBuildAssetMap:
    def test_uses_equipment_id_when_uppercase_hyphenated(self):
        asset_map = build_asset_map([ASSET_ACTIVE])
        assert asset_map[1] == "MMC-CHIL-001"

    def test_derives_slug_when_id_empty(self):
        asset_map = build_asset_map([ASSET_NO_EID])
        result = asset_map[99]
        assert result.startswith("PUMP-") or result.startswith("HWP-") or "-" in result

    def test_derives_slug_when_id_not_uppercase_hyphen(self):
        asset_map = build_asset_map([ASSET_LOWERCASE_EID])
        result = asset_map[50]
        # "pump-001" doesn't match uppercase-hyphen pattern → slug from description
        assert result == "BOIL-001"

    def test_multiple_assets(self):
        assets = [ASSET_ACTIVE, ASSET_NO_EID]
        asset_map = build_asset_map(assets)
        assert len(asset_map) == 2
        assert asset_map[1] == "MMC-CHIL-001"

    def test_handles_pascal_case_keys(self):
        # Some FaciliWorks responses use PascalCase
        asset = {
            "EquipmentMasterID": 7,
            "EquipmentID": "MMC-VFD-001",
            "description": "Chiller VFD",
        }
        asset_map = build_asset_map([asset])
        assert asset_map[7] == "MMC-VFD-001"


# ── map_work_order ────────────────────────────────────────────────────────────

class TestMapWorkOrder:
    @pytest.fixture
    def asset_map(self):
        return build_asset_map([ASSET_ACTIVE, {
            "equipmentMasterID": 3,
            "equipmentID": "MMC-CTW-001",
            "description": "Cooling Tower #1",
        }])

    def test_cm_complete_fields(self, asset_map):
        result = map_work_order(CM_COMPLETE, asset_map, "Corrective")
        assert result is not None
        assert result["work_order_id"] == "CM-1001"
        assert result["asset_id"] == "MMC-CHIL-001"
        assert result["type"] == "Corrective"
        assert result["status"] == "Completed"
        assert result["priority"] == "High"
        assert result["labor_hours_scheduled"] == 3.0
        assert result["labor_hours_actual"] == 2.5

    def test_cm_complete_has_completion_date(self, asset_map):
        result = map_work_order(CM_COMPLETE, asset_map, "Corrective")
        assert result["completion_date"] is not None
        assert len(result["completion_date"]) == 10  # YYYY-MM-DD

    def test_cm_open_past_due_inferred_completed(self, asset_map):
        result = map_work_order(CM_OPEN_PAST_DUE, asset_map, "Corrective")
        # past due + open → inferred as completed
        assert result["status"] == "Completed"
        assert result["completion_date"] == result["due_date"]

    def test_pm_open_future_due_stays_open(self, asset_map):
        result = map_work_order(PM_OPEN, asset_map, "Preventive")
        assert result["status"] == "Open"
        assert result["completion_date"] is None

    def test_unknown_asset_returns_none(self, asset_map):
        result = map_work_order(CM_NO_ASSET, asset_map, "Corrective")
        assert result is None

    def test_pm_complete_is_preventive(self, asset_map):
        result = map_work_order(PM_COMPLETE, asset_map, "Preventive")
        assert result["type"] == "Preventive"
        assert result["status"] == "Completed"

    def test_corrective_high_priority_sets_reactive_followup(self, asset_map):
        result = map_work_order(CM_COMPLETE, asset_map, "Corrective")
        assert result["reactive_followup"] == 1

    def test_pm_does_not_set_reactive_followup(self, asset_map):
        result = map_work_order(PM_COMPLETE, asset_map, "Preventive")
        assert result["reactive_followup"] == 0

    def test_corrective_medium_priority_no_reactive_followup(self, asset_map):
        result = map_work_order(CM_OPEN_PAST_DUE, asset_map, "Corrective")
        assert result["reactive_followup"] == 0

    def test_all_required_keys_present(self, asset_map):
        result = map_work_order(CM_COMPLETE, asset_map, "Corrective")
        required = [
            "work_order_id", "asset_id", "site", "type", "status", "technician",
            "creation_date", "scheduled_start", "start_date", "completion_date",
            "labor_hours_scheduled", "labor_hours_actual", "downtime_hours",
            "reactive_followup", "priority", "due_date",
        ]
        for key in required:
            assert key in result, f"Missing key: {key}"

    def test_wo_number_preferred_over_maintenance_key(self, asset_map):
        result = map_work_order(CM_COMPLETE, asset_map, "Corrective")
        assert result["work_order_id"] == "CM-1001"  # woNumber, not maintenanceKey

    def test_falls_back_to_maintenance_key_when_no_wonumber(self, asset_map):
        wo = {**CM_COMPLETE, "woNumber": None, "maintenanceKey": 9999}
        result = map_work_order(wo, asset_map, "Corrective")
        assert result["work_order_id"] == "9999"
