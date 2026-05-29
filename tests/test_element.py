from lfdata.video.element import UIElement, UIElementStyle


def test_ui_element_style_defaults() -> None:
    style = UIElementStyle()
    assert style.font == 'GoogleSans-Bold'
    assert style.style == 'normal'
    assert style.size == 20
    assert style.color == '#ffffffff'
    assert style.background_color == '#00000000'


def test_ui_element_initialization() -> None:
    element = UIElement(
        element_type='text',
        position='top left',
        text='Score: 100',
        safe_ms=1000,
        resettable_ms=2000,
    )
    assert element.element_type == 'text'
    assert element.position == 'top left'
    assert element.text == 'Score: 100'
    assert element.safe_ms == 1000
    assert element.resettable_ms == 2000
    assert element.style.font == 'GoogleSans-Bold'
