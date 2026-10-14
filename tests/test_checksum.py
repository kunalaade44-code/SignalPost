from signalpost.core.checksum import calculate_control_digit, validate_org_number


class TestChecksum:
    def test_valid_real_norwegian_org_numbers(self):
        # Known real Norwegian organization numbers
        valid_numbers = [
            "923609016",  # Equinor ASA
            "984851006",  # DNB Bank ASA
            "976967631",  # Telenor ASA
            "917088713",  # Norsk Hydro ASA
            "938708606",  # Schibsted ASA
            "983044697",  # Posten Norge AS
            "936809286",  # Valid mod-11 orgnr
            "984054564",  # Yara International ASA
        ]
        for orgnr in valid_numbers:
            is_valid, clean = validate_org_number(orgnr)
            assert is_valid is True, f"Failed for {orgnr}: {clean}"
            assert clean == orgnr

    def test_formatted_org_numbers_with_spaces_and_dots(self):
        is_valid, clean = validate_org_number("923 609 016")
        assert is_valid is True
        assert clean == "923609016"

        is_valid, clean = validate_org_number("984.851.006")
        assert is_valid is True
        assert clean == "984851006"

    def test_invalid_length(self):
        is_valid, reason = validate_org_number("12345678")  # 8 digits
        assert is_valid is False
        assert "exactly 9 digits" in reason

        is_valid, reason = validate_org_number("1234567890")  # 10 digits
        assert is_valid is False
        assert "exactly 9 digits" in reason

    def test_non_digit_characters(self):
        is_valid, reason = validate_org_number("92360901A")
        assert is_valid is False
        assert "digits only" in reason

    def test_corrupted_control_digit(self):
        # Valid is 923609016. Change last digit to 5:
        is_valid, reason = validate_org_number("923609015")
        assert is_valid is False
        assert "Checksum mismatch" in reason

    def test_calculate_control_digit(self):
        # 92360901 -> 6
        ctrl = calculate_control_digit("92360901")
        assert ctrl == 6

        # 98485100 -> 6
        ctrl2 = calculate_control_digit("98485100")
        assert ctrl2 == 6
