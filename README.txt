To render Bangla / Hindi / Urdu / Arabic captions correctly in generated
images (meme, fakechat, friendship card), download a font that covers that
script and save it here as exactly:

    script_font.ttf

Recommended (free, covers Bangla + Latin):
    Google Fonts -> "Noto Sans Bengali"
    https://fonts.google.com/noto/specimen/Noto+Sans+Bengali

For Arabic/Urdu specifically, "Noto Naskh Arabic" or "Noto Sans Arabic"
render better. You can only have one script_font.ttf active at a time in
this simple setup — if you need multiple scripts well-rendered
simultaneously, edit utils/image_gen.py's get_font() to pick a font based
on the detected script of the text.

Without this file, non-Latin text will likely render as empty boxes (□□□)
in generated images — English/Latin captions work fine either way using the
bundled DejaVu Sans Bold font.
