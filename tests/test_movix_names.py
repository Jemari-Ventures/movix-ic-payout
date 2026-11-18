from movix_dispatcher.names import clean_driver_name


def test_strips_id_and_okar_prefix():
    assert (
        clean_driver_name("[305572]OKAR - D - MUHAMMAD SYUKRI BIN ABU ASAN")
        == "MUHAMMAD SYUKRI BIN ABU ASAN"
    )


def test_strips_okar_only():
    assert clean_driver_name("OKAR - D - ROSLAINI BINTI MOHD JALANI") == "ROSLAINI BINTI MOHD JALANI"


def test_leaves_plain_name():
    assert clean_driver_name("Test Driver") == "Test Driver"
