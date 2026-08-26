import pytest
from app.models.tprm import (
    BusinessCriticalityEnum,
    DataClassificationEnum,
    EngagementStatusEnum,
    HostingModelEnum,
    NetworkConnectivityEnum,
    PiiFinancialAccessEnum,
    Vendor,
    VendorAssessment,
    VendorAssessmentItem,
    VendorAssessmentStatusEnum,
    VendorEngagement,
    VendorResponseStatusEnum,
    VendorRiskBandEnum,
    VendorStatusEnum,
    VendorTierEnum,
)
from app.services.tprm_service import TPRMService


class TestTPRMEngine:
    """Comprehensive test suite for Phase 9 TPRM mathematical & scoring engines."""

    def test_inherent_risk_calculation_formula(self):
        """0.30*C + 0.30*D + 0.20*N + 0.10*P + 0.10*H normalized 0.0 - 100.0."""
        # Critical(100), Restricted(100), DirectAPI(100), DirectPCI(100), MultiTenantSaaS(100)
        # 30 + 30 + 20 + 10 + 10 = 100.0
        risk_max = TPRMService.calculate_engagement_risk(
            criticality=BusinessCriticalityEnum.CRITICAL,
            data_classification=DataClassificationEnum.RESTRICTED,
            network=NetworkConnectivityEnum.DIRECT_API_VPN_DB,
            pii=PiiFinancialAccessEnum.DIRECT_PCI_PII_PHI,
            hosting=HostingModelEnum.MULTI_TENANT_SAAS,
        )
        assert risk_max == 100.0

        # Low(25), Public(10), Isolated(10), None(0), OnPremise(40)
        # 0.30*25 (7.5) + 0.30*10 (3.0) + 0.20*10 (2.0) + 0.10*0 (0.0) + 0.10*40 (4.0) = 16.5
        risk_min = TPRMService.calculate_engagement_risk(
            criticality=BusinessCriticalityEnum.LOW,
            data_classification=DataClassificationEnum.PUBLIC,
            network=NetworkConnectivityEnum.ISOLATED_NO_CONNECTION,
            pii=PiiFinancialAccessEnum.NONE,
            hosting=HostingModelEnum.ON_PREMISE,
        )
        assert risk_min == 16.5

    def test_maximum_active_engagement_risk_selection(self):
        """Vendor inherent risk is the maximum risk among ACTIVE engagements only."""
        e1 = VendorEngagement(
            engagement_code="ENG-01",
            engagement_name="Low Risk Active",
            status=EngagementStatusEnum.ACTIVE,
            criticality=BusinessCriticalityEnum.LOW,
            data_classification=DataClassificationEnum.PUBLIC,
            network_connectivity=NetworkConnectivityEnum.ISOLATED_NO_CONNECTION,
            pii_access=PiiFinancialAccessEnum.NONE,
            hosting_model=HostingModelEnum.ON_PREMISE,
        )
        e2 = VendorEngagement(
            engagement_code="ENG-02",
            engagement_name="High Risk Inactive",
            status=EngagementStatusEnum.INACTIVE,  # Inactive must be ignored
            criticality=BusinessCriticalityEnum.CRITICAL,
            data_classification=DataClassificationEnum.RESTRICTED,
            network_connectivity=NetworkConnectivityEnum.DIRECT_API_VPN_DB,
            pii_access=PiiFinancialAccessEnum.DIRECT_PCI_PII_PHI,
            hosting_model=HostingModelEnum.MULTI_TENANT_SAAS,
        )
        e3 = VendorEngagement(
            engagement_code="ENG-03",
            engagement_name="Medium Risk Active",
            status=EngagementStatusEnum.ACTIVE,
            criticality=BusinessCriticalityEnum.MEDIUM,
            data_classification=DataClassificationEnum.INTERNAL,
            network_connectivity=NetworkConnectivityEnum.CORPORATE_SSO,
            pii_access=PiiFinancialAccessEnum.METADATA_ONLY,
            hosting_model=HostingModelEnum.DEDICATED_CLOUD,
        )
        # e1 risk = 16.5
        # e3 risk = 0.3*50(15) + 0.3*50(15) + 0.2*50(10) + 0.1*40(4) + 0.1*70(7) = 51.0

        inherent_risk, tier = TPRMService.calculate_vendor_inherent_risk_and_tier([e1, e2, e3])
        assert inherent_risk == 51.0
        assert tier == VendorTierEnum.TIER_3_MODERATE

    def test_deterministic_tier_mapping(self):
        """Inherent risk >= 80 -> TIER_1, 60-79.9 -> TIER_2, 40-59.9 -> TIER_3, <40 -> TIER_4."""
        # Tier 4 (<40)
        e_low = VendorEngagement(
            engagement_code="ENG-L",
            engagement_name="Low",
            status=EngagementStatusEnum.ACTIVE,
            criticality=BusinessCriticalityEnum.LOW,
            data_classification=DataClassificationEnum.PUBLIC,
            network_connectivity=NetworkConnectivityEnum.ISOLATED_NO_CONNECTION,
            pii_access=PiiFinancialAccessEnum.NONE,
            hosting_model=HostingModelEnum.ON_PREMISE,
        )
        risk, tier = TPRMService.calculate_vendor_inherent_risk_and_tier([e_low])
        assert risk == 16.5
        assert tier == VendorTierEnum.TIER_4_LOW

        # Tier 2 (60-79.9)
        e_sig = VendorEngagement(
            engagement_code="ENG-S",
            engagement_name="Significant",
            status=EngagementStatusEnum.ACTIVE,
            criticality=BusinessCriticalityEnum.HIGH,  # 75 -> 22.5
            data_classification=DataClassificationEnum.CONFIDENTIAL,  # 75 -> 22.5
            network_connectivity=NetworkConnectivityEnum.CORPORATE_SSO,  # 50 -> 10.0
            pii_access=PiiFinancialAccessEnum.METADATA_ONLY,  # 40 -> 4.0
            hosting_model=HostingModelEnum.MULTI_TENANT_SAAS,  # 100 -> 10.0 => 69.0
        )
        risk_sig, tier_sig = TPRMService.calculate_vendor_inherent_risk_and_tier([e_sig])
        assert risk_sig == 69.0
        assert tier_sig == VendorTierEnum.TIER_2_SIGNIFICANT

    def test_critical_engagement_forcing_tier_1(self):
        """Even if inherent risk score is < 80, any active engagement with CRITICAL criticality forces TIER_1_CRITICAL."""
        e_crit = VendorEngagement(
            engagement_code="ENG-CRIT",
            engagement_name="Critical Criticality but low data",
            status=EngagementStatusEnum.ACTIVE,
            criticality=BusinessCriticalityEnum.CRITICAL,  # 100 -> 30.0
            data_classification=DataClassificationEnum.INTERNAL,  # 50 -> 15.0
            network_connectivity=NetworkConnectivityEnum.ISOLATED_NO_CONNECTION,  # 10 -> 2.0
            pii_access=PiiFinancialAccessEnum.NONE,  # 0 -> 0.0
            hosting_model=HostingModelEnum.ON_PREMISE,  # 40 -> 4.0 => 51.0
        )
        risk, tier = TPRMService.calculate_vendor_inherent_risk_and_tier([e_crit])
        assert risk == 51.0
        assert tier == VendorTierEnum.TIER_1_CRITICAL

    def test_assessment_score_calculation_weights(self):
        """Assessment score = (sum(w*r) / sum(w)) * 100.0."""
        item1 = VendorAssessmentItem(
            question_key="Q1",
            question_text="MFA",
            response_status=VendorResponseStatusEnum.COMPLIANT,  # 1.0 * 2.0 = 2.0
            weight=2.0,
        )
        item2 = VendorAssessmentItem(
            question_key="Q2",
            question_text="Encryption",
            response_status=VendorResponseStatusEnum.PARTIALLY_COMPLIANT,  # 0.5 * 1.0 = 0.5
            weight=1.0,
        )
        item3 = VendorAssessmentItem(
            question_key="Q3",
            question_text="Pen Test",
            response_status=VendorResponseStatusEnum.NON_COMPLIANT,  # 0.0 * 1.0 = 0.0
            weight=1.0,
        )
        # Total weighted = 2.5 / 4.0 = 0.625 -> 62.5%
        score = TPRMService.calculate_assessment_score([item1, item2, item3])
        assert score == 62.5

    def test_assessment_score_not_applicable_exclusion(self):
        """NOT_APPLICABLE items are excluded from both numerator and denominator."""
        item1 = VendorAssessmentItem(
            question_key="Q1",
            question_text="MFA",
            response_status=VendorResponseStatusEnum.COMPLIANT,  # 1.0 * 1.0
            weight=1.0,
        )
        item2 = VendorAssessmentItem(
            question_key="Q2",
            question_text="FedRAMP",
            response_status=VendorResponseStatusEnum.NOT_APPLICABLE,  # Ignored
            weight=5.0,
        )
        score = TPRMService.calculate_assessment_score([item1, item2])
        assert score == 100.0

    def test_all_na_assessment_scores_100(self):
        """If all items are NOT_APPLICABLE, score defaults to 100.0%."""
        item1 = VendorAssessmentItem(
            question_key="Q1",
            question_text="FedRAMP",
            response_status=VendorResponseStatusEnum.NOT_APPLICABLE,
            weight=1.0,
        )
        score = TPRMService.calculate_assessment_score([item1])
        assert score == 100.0

    def test_residual_risk_floor_enforcement(self):
        """Residual risk cannot attenuate below 0.20 * InherentRisk even with 100% assessment score."""
        inherent_risk = 80.0
        # Risk floor = 0.20 * 80 = 16.0
        # Base residual = 80 * (1 - 0.7*1.0) = 80 * 0.30 = 24.0
        residual, band = TPRMService.calculate_vendor_residual_risk(
            inherent_risk=inherent_risk,
            latest_assessment_score=100.0,
            finding_penalties=0.0,
            exception_penalties=0.0,
        )
        assert residual == 24.0
        assert band == VendorRiskBandEnum.LOW

    def test_seventy_percent_assessment_attenuation_ceiling(self):
        """100% assessment score attenuates inherent risk by at most 70% (leaves 30% baseline)."""
        inherent_risk = 100.0
        # Base residual = 100 * (1 - 0.70) = 30.0
        residual, band = TPRMService.calculate_vendor_residual_risk(
            inherent_risk=inherent_risk,
            latest_assessment_score=100.0,
        )
        assert residual == 30.0
        assert band == VendorRiskBandEnum.LOW

    def test_finding_and_exception_penalties_accumulation(self):
        """Finding penalties (+15 critical, +8 high, +3 medium) and exceptions (+10) add to residual risk."""
        inherent_risk = 50.0
        # Base residual = 50.0 * (1 - 0.7*1.0) = 15.0. Floor = 0.2*50 = 10.0 -> max(10, 15) = 15.0
        # Critical finding (+15) + High finding (+8) + Exception (+10) = +33.0
        # Total residual = 15.0 + 33.0 = 48.0
        residual, band = TPRMService.calculate_vendor_residual_risk(
            inherent_risk=inherent_risk,
            latest_assessment_score=100.0,
            finding_penalties=23.0,
            exception_penalties=10.0,
        )
        assert residual == 48.0
        assert band == VendorRiskBandEnum.MODERATE

    def test_residual_risk_clamping_to_100(self):
        """Residual risk cannot exceed 100.0."""
        inherent_risk = 90.0
        residual, band = TPRMService.calculate_vendor_residual_risk(
            inherent_risk=inherent_risk,
            latest_assessment_score=0.0,
            finding_penalties=50.0,
            exception_penalties=20.0,
        )
        assert residual == 100.0
        assert band == VendorRiskBandEnum.CRITICAL

    def test_risk_band_boundaries(self):
        """Verify strict risk band boundaries: <40 LOW, 40-59.9 MODERATE, 60-79.9 HIGH, >=80 CRITICAL."""
        r39, b39 = TPRMService.calculate_vendor_residual_risk(39.9, 0.0)
        assert b39 == VendorRiskBandEnum.LOW

        r40, b40 = TPRMService.calculate_vendor_residual_risk(40.0, 0.0)
        assert b40 == VendorRiskBandEnum.MODERATE

        r60, b60 = TPRMService.calculate_vendor_residual_risk(60.0, 0.0)
        assert b60 == VendorRiskBandEnum.HIGH

        r80, b80 = TPRMService.calculate_vendor_residual_risk(80.0, 0.0)
        assert b80 == VendorRiskBandEnum.CRITICAL
