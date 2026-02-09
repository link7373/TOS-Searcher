from tos_searcher.scraper.parser import DocumentParser


def test_extract_text_basic() -> None:
    parser = DocumentParser()
    html = """
    <html>
    <head><title>Terms</title></head>
    <body>
        <nav><a href="/">Home</a><a href="/about">About</a></nav>
        <main>
            <h1>Terms of Service</h1>
            <p>By using our service, you agree to these terms.</p>
            <p>We reserve the right to modify these terms.</p>
        </main>
        <footer>Copyright 2024</footer>
    </body>
    </html>
    """
    text = parser.extract_text(html)
    assert "Terms of Service" in text
    assert "By using our service" in text
    # Nav and footer should be removed
    assert "Home" not in text
    assert "Copyright 2024" not in text


def test_extract_text_strips_scripts() -> None:
    parser = DocumentParser()
    html = """
    <html><body>
        <script>var x = 'malicious';</script>
        <p>Real content here.</p>
        <style>.hidden { display: none; }</style>
    </body></html>
    """
    text = parser.extract_text(html)
    assert "Real content" in text
    assert "malicious" not in text
    assert ".hidden" not in text


def test_extract_text_finds_main_content() -> None:
    parser = DocumentParser()
    html = """
    <html><body>
        <div class="sidebar">Sidebar stuff</div>
        <article>
            <h1>Privacy Policy</h1>
            <p>We respect your privacy.</p>
        </article>
    </body></html>
    """
    text = parser.extract_text(html)
    assert "Privacy Policy" in text
    assert "We respect your privacy" in text


def test_extract_title() -> None:
    parser = DocumentParser()
    html = "<html><head><title>Terms of Service - ACME Corp</title></head><body></body></html>"
    title = parser.extract_title(html)
    assert title == "Terms of Service - ACME Corp"


def test_extract_title_missing() -> None:
    parser = DocumentParser()
    html = "<html><head></head><body>No title here</body></html>"
    title = parser.extract_title(html)
    assert title == ""
