"""
Testes de unidade da integração com o YouTube.

Só as funções puras — extrair id de URL e reconhecer playlist. O que
depende de rede (oEmbed e feed) não é testado aqui: teste de unidade que
sai para a internet falha por motivo errado quando a conexão cai.
"""

import pytest

from app.services.youtube import extrair_id, extrair_playlist_id


class TestExtrairIdDeVideo:
    @pytest.mark.parametrize(
        "url",
        [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtu.be/dQw4w9WgXcQ",
            "https://www.youtube.com/embed/dQw4w9WgXcQ",
            "https://www.youtube.com/shorts/dQw4w9WgXcQ",
            "https://www.youtube.com/live/dQw4w9WgXcQ",
            "dQw4w9WgXcQ",
        ],
    )
    def test_reconhece_todos_os_formatos(self, url):
        assert extrair_id(url) == "dQw4w9WgXcQ"

    def test_ignora_o_que_vem_depois_do_id(self):
        # É o link que o YouTube dá quando você compartilha no meio do vídeo.
        assert (
            extrair_id("https://youtu.be/dQw4w9WgXcQ?t=42") == "dQw4w9WgXcQ"
        )
        assert (
            extrair_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PL123&index=2")
            == "dQw4w9WgXcQ"
        )

    @pytest.mark.parametrize(
        "entrada",
        ["https://vimeo.com/12345", "texto qualquer", "", "https://youtube.com"],
    )
    def test_recusa_o_que_nao_e_video(self, entrada):
        assert extrair_id(entrada) is None

    def test_id_precisa_ter_onze_caracteres(self):
        assert extrair_id("curtoDemais") == "curtoDemais"  # exatamente 11
        assert extrair_id("curto") is None
        assert extrair_id("esse_id_e_longo_demais") is None


class TestExtrairPlaylist:
    def test_reconhece_o_list_da_url(self):
        url = "https://www.youtube.com/watch?v=abc12345678&list=PLHL_oeAq-y70XJ8"
        assert extrair_playlist_id(url) == "PLHL_oeAq-y70XJ8"

    def test_link_de_video_avulso_nao_tem_playlist(self):
        assert extrair_playlist_id("https://youtu.be/dQw4w9WgXcQ") is None

    def test_texto_vazio_nao_quebra(self):
        assert extrair_playlist_id("") is None
        assert extrair_playlist_id(None) is None
