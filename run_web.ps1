# 启动 Streamlit Web UI（不依赖 streamlit 是否在 PATH 里）
Set-Location $PSScriptRoot
$env:STREAMLIT_SERVER_HEADLESS = "true"
py -m streamlit run web/app.py
