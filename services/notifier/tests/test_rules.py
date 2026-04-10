import pytest
import yaml
import os
from unittest.mock import patch, MagicMock
from app.main import NotifierService


class TestRulesLoading:
    """Test rules YAML loading functionality."""

    def test_load_rules_success(self, tmp_path, sample_rules):
        """Test successful rules loading."""
        rules_file = tmp_path / "rules.yaml"
        rules_file.write_text(yaml.dump({"rules": sample_rules}))
        
        service = NotifierService()
        
        with patch("app.main.os.path.dirname") as mock_dirname:
            mock_dirname.return_value = str(tmp_path)
            with patch("app.main.os.path.join", side_effect=lambda *args: str(rules_file)):
                service.load_rules()
        
        assert len(service.rules) == 3
        assert service.rules[0]["datastream_id"] == "test-ds-1"
        assert service.rules[0]["name"] == "High Temperature"

    def test_load_rules_empty_file(self, tmp_path):
        """Test loading empty rules file."""
        rules_file = tmp_path / "rules.yaml"
        rules_file.write_text(yaml.dump({}))
        
        service = NotifierService()
        
        with patch("app.main.os.path.dirname") as mock_dirname:
            mock_dirname.return_value = str(tmp_path)
            with patch("app.main.os.path.join", side_effect=lambda *args: str(rules_file)):
                service.load_rules()
        
        assert service.rules == []

    def test_load_rules_file_not_found(self):
        """Test handling of missing rules file."""
        service = NotifierService()
        
        with patch("app.main.os.path.dirname") as mock_dirname:
            mock_dirname.return_value = "/fake/path"
            with patch("app.main.os.path.join", side_effect=lambda *args: "/fake/path/rules.yaml"):
                service.load_rules()
        
        # Should handle gracefully and leave rules empty
        assert service.rules == []

    def test_load_rules_malformed_yaml(self, tmp_path):
        """Test handling of malformed YAML."""
        rules_file = tmp_path / "rules.yaml"
        rules_file.write_text("invalid: yaml: content: [")
        
        service = NotifierService()
        
        with patch("app.main.os.path.dirname") as mock_dirname:
            mock_dirname.return_value = str(tmp_path)
            with patch("app.main.os.path.join", side_effect=lambda *args: str(rules_file)):
                service.load_rules()
        
        assert service.rules == []


class TestRuleStructure:
    """Test individual rule structure validation."""

    def test_threshold_rule_structure(self, sample_rules):
        """Verify threshold alert rule has required fields."""
        rule = sample_rules[0]
        
        assert "datastream_id" in rule
        assert "name" in rule
        assert "condition" in rule
        assert "threshold" in rule
        assert "priority" in rule
        assert "cooldown_minutes" in rule

    def test_system_metric_rule_structure(self, sample_rules):
        """Verify system metric rule has required fields."""
        rule = sample_rules[2]
        
        assert "type" in rule
        assert rule["type"] == "system_metric"
        assert "metric" in rule
        assert "name" in rule
        assert "condition" in rule
        assert "threshold" in rule
