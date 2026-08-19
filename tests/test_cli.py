from ai_observatory.cli import main


def test_health_command_prints_chinese_status(capsys):
    assert main(["health"]) == 0
    assert capsys.readouterr().out.strip() == "AI Research Observatory：运行正常"
