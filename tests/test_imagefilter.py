from imagefilter import ImageInfo, drop_reasons

A4 = 595 * 842


def img(page=1, w=300, h=200, digest="a", text=True):
    return ImageInfo(page=page, width_pt=w, height_pt=h, page_area_pt=A4, digest=digest, page_has_text=text)


def test_regular_figure_kept():
    assert drop_reasons([img()]) == [None]


def test_icon_dropped():
    assert drop_reasons([img(w=16, h=16)]) == ["small"]


def test_tiny_area_dropped():
    assert drop_reasons([img(w=120, h=60)]) == ["small"]


def test_logo_on_three_pages_dropped():
    assert drop_reasons([img(page=p, digest="logo") for p in (1, 2, 3)]) == ["repeated"] * 3


def test_same_image_on_two_pages_kept():
    assert drop_reasons([img(page=p, digest="x") for p in (1, 2)]) == [None, None]


def test_banner_dropped():
    assert drop_reasons([img(w=500, h=40)]) == ["banner"]


def test_background_dropped_only_when_page_has_text():
    full_with_text = img(w=595, h=842, digest="a", text=True)
    full_without_text = img(w=595, h=842, digest="b", text=False)
    assert drop_reasons([full_with_text, full_without_text]) == ["background", None]
