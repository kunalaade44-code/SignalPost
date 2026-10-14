from signalpost.core.normalizer import (
    calculate_name_similarity,
    normalize_company_name,
    transliterate_norwegian,
)


class TestNormalizer:
    def test_transliterate_norwegian(self):
        assert transliterate_norwegian("blåbær") == "blaabaer"
        assert transliterate_norwegian("møre og romsdal") == "moere og romsdal"
        assert transliterate_norwegian("BLÅ") == "BLAA"

    def test_normalize_company_name_strips_legal_forms(self):
        assert normalize_company_name("EQUINOR ASA") == "equinor"
        assert normalize_company_name("Acme Aksjeselskap") == "acme"
        assert normalize_company_name("Nordic Tech ENK") == "nordic tech"
        assert normalize_company_name("Viken Consult NUF") == "viken consult"
        assert normalize_company_name("Fjord Holding AS") == "fjord"

    def test_normalize_company_name_handles_special_characters(self):
        assert normalize_company_name("H. & M. Hennes & Mauritz AS") == "h m hennes mauritz"
        assert normalize_company_name("Øyvind's Rør AS") == "oeyvinds roer"

    def test_calculate_name_similarity_high_matches(self):
        # Legal form variation
        score = calculate_name_similarity("Equinor ASA", "Equinor AS")
        assert score >= 0.95

        # Punctuation and case variation
        score = calculate_name_similarity("Schibsted Media Group AS", "schibsted media")
        assert score >= 0.85

        # Transliteration match
        score = calculate_name_similarity("Blåbær Data AS", "Blaabaer Data")
        assert score >= 0.95

    def test_calculate_name_similarity_distinct_companies(self):
        # Completely distinct entities
        score = calculate_name_similarity("Equinor ASA", "Telenor ASA")
        assert score < 0.60

        # Partial token overlap ('bank') stays below 0.70 and far below 0.90 match threshold
        score = calculate_name_similarity("DNB Bank ASA", "Nordea Bank Abp")
        assert score < 0.70
        assert score < 0.90
