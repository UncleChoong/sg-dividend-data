from unittest.mock import patch, MagicMock
from sg_dividend_data.uploader import upload_to_r2


def test_upload_to_r2_calls_boto(monkeypatch, tmp_path):
    monkeypatch.setenv("R2_ACCOUNT_ID", "acct")
    monkeypatch.setenv("R2_ACCESS_KEY_ID", "k")
    monkeypatch.setenv("R2_SECRET_ACCESS_KEY", "s")
    monkeypatch.setenv("R2_BUCKET", "bkt")
    f = tmp_path / "u.json"
    f.write_text("{}")
    with patch("sg_dividend_data.uploader.boto3.client") as cli:
        s3 = MagicMock()
        cli.return_value = s3
        upload_to_r2(f, key="sg_dividend_universe.json")
    cli.assert_called_once()
    s3.upload_file.assert_called_once_with(str(f), "bkt", "sg_dividend_universe.json",
                                            ExtraArgs={"ContentType": "application/json",
                                                       "CacheControl": "public, max-age=300"})
