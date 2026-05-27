"""
Módulo de autenticação — S&OE Inteligência Comercial.

Arquitetura:
  - Credenciais armazenadas em .streamlit/secrets.toml (gitignored).
  - Senhas nunca ficam em texto limpo: apenas hashes bcrypt (rounds=12).
  - Estado de sessão gerenciado via st.session_state (server-side, não exposto
    ao browser como cookie ou query string).
  - F5 / reconexão → sessão limpa → usuário deve logar novamente (comportamento
    correto para um painel com dados confidenciais).
  - Proteção básica contra brute-force: trava após 5 tentativas por 5 minutos.

API pública:
  require_auth()          → bloqueia e exibe tela de login se não autenticado.
  render_sidebar_user()   → injeta nome do usuário + botão Sair na sidebar.
  get_current_user()      → retorna dict com email/name/role do usuário ativo.
  logout()                → limpa sessão e redireciona para o login.
"""
from __future__ import annotations

from datetime import datetime, timedelta

import bcrypt
import streamlit as st

# ── Chaves de session_state (prefixadas com _ para não colidir) ───────────────
_K_OK       = "_auth_ok"        # bool — autenticado?
_K_USER     = "_auth_user"      # dict — dados do usuário
_K_ATTEMPTS = "_auth_attempts"  # int  — tentativas erradas consecutivas
_K_LOCKED   = "_auth_locked"    # datetime — bloqueado até

_MAX_ATTEMPTS  = 5              # tentativas antes de bloquear
_LOCKOUT_MIN   = 5              # minutos de bloqueio


# ── Funções internas ──────────────────────────────────────────────────────────

def _verify_password(password: str, hashed: str) -> bool:
    """Compara senha em texto com hash bcrypt de forma segura."""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def _load_users() -> list[dict]:
    """
    Carrega lista de usuários de st.secrets['users'].
    Cada entrada pode ter 'email' OU 'username' como identificador de login.
    """
    try:
        raw = st.secrets["users"]
        return [dict(v) for v in raw.values()]
    except Exception:
        return []


def _find_user(login: str, password: str) -> dict | None:
    """
    Procura usuário pelo identificador (e-mail ou username) e verifica senha.
    Retorna dict com dados do usuário ou None se credenciais inválidas.
    """
    login_norm = login.strip().lower()
    for user in _load_users():
        identifier = (user.get("email") or user.get("username", "")).lower()
        if identifier == login_norm:
            if _verify_password(password, user.get("hash", "")):
                return user
    return None


def _is_locked() -> bool:
    """Verifica se o IP/sessão está bloqueado por excesso de tentativas."""
    locked_until = st.session_state.get(_K_LOCKED)
    if locked_until and datetime.now() < locked_until:
        return True
    # Expirou o bloqueio — limpa
    if locked_until:
        st.session_state.pop(_K_LOCKED, None)
        st.session_state[_K_ATTEMPTS] = 0
    return False


def _register_failed_attempt() -> None:
    """Incrementa contador de falhas e bloqueia se necessário."""
    attempts = st.session_state.get(_K_ATTEMPTS, 0) + 1
    st.session_state[_K_ATTEMPTS] = attempts
    if attempts >= _MAX_ATTEMPTS:
        st.session_state[_K_LOCKED] = datetime.now() + timedelta(minutes=_LOCKOUT_MIN)
        st.session_state[_K_ATTEMPTS] = 0


def _reset_attempts() -> None:
    st.session_state.pop(_K_ATTEMPTS, None)
    st.session_state.pop(_K_LOCKED, None)


# ── API pública ───────────────────────────────────────────────────────────────

def is_authenticated() -> bool:
    return bool(st.session_state.get(_K_OK, False))


def get_current_user() -> dict:
    return st.session_state.get(_K_USER, {})


def logout() -> None:
    """Limpa toda a sessão de autenticação e recarrega o app."""
    for key in [_K_OK, _K_USER, _K_ATTEMPTS, _K_LOCKED]:
        st.session_state.pop(key, None)
    st.rerun()


def require_auth() -> None:
    """
    Gate principal de autenticação.
    Se o usuário NÃO estiver autenticado, exibe a tela de login e chama
    st.stop() — todo o restante do dashboard.py é bloqueado.
    Se estiver autenticado, retorna imediatamente (execução continua).
    """
    if is_authenticated():
        return
    _render_login()
    st.stop()


def render_sidebar_user() -> None:
    """
    Deve ser chamado dentro do bloco `with st.sidebar:` do dashboard.
    Injeta o nome/papel do usuário logado e o botão de logout.
    """
    user  = get_current_user()
    name  = user.get("name", "Usuário")
    role  = user.get("role", "")
    role_label = {
        "comercial":    "Coordenador Comercial",
        "planejamento": "Planejamento Integrado",
    }.get(role, role.title() if role else "Acesso Geral")

    st.sidebar.markdown(
        f'<div style="background:#F0F4FA;border-radius:10px;border-left:4px solid #1B2A4A;padding:10px 14px;margin-bottom:8px;">'
        f'<div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.6px;color:#6C757D;margin-bottom:2px;">Usuário conectado</div>'
        f'<div style="font-size:13px;font-weight:700;color:#1B2A4A;">&#x1F464; {name}</div>'
        f'<div style="font-size:11px;color:#9EA8B3;margin-top:1px;">{role_label}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    if st.sidebar.button(
        "🚪 Sair / Log Out",
        use_container_width=True,
        key="_auth_logout_btn",
        type="secondary",
    ):
        logout()


# ── Tela de login ─────────────────────────────────────────────────────────────

def _render_login() -> None:
    """Renderiza a tela de login centralizada e bloqueia a sidebar."""

    # CSS: fundo escuro, sidebar oculta, inputs estilizados
    st.markdown(
        """
        <style>
        /* ── Esconde a sidebar e o botão de expandir ── */
        [data-testid="stSidebar"]        { display: none !important; }
        [data-testid="collapsedControl"] { display: none !important; }

        /* ── Fundo da página ── */
        .stApp {
            background: linear-gradient(150deg, #1B2A4A 0%, #16374E 60%, #0F2336 100%) !important;
        }

        /* ── Remove padding padrão do main ── */
        .block-container {
            padding-top: 5vh !important;
            max-width: 100% !important;
        }

        /* ── Botão de submit do login ── */
        div[data-testid="stFormSubmitButton"] button {
            background-color: #D96B2D !important;
            color: white !important;
            font-weight: 700 !important;
            border: none !important;
            border-radius: 8px !important;
            padding: 0.6rem 1rem !important;
            font-size: 15px !important;
            transition: background .2s ease;
        }
        div[data-testid="stFormSubmitButton"] button:hover {
            background-color: #C05A20 !important;
        }

        /* ── Inputs do formulário ── */
        .stTextInput input {
            border-radius: 8px !important;
            border: 1.5px solid #D0D8E4 !important;
            padding: 0.55rem 0.75rem !important;
            font-size: 14px !important;
            background: #ffffff !important;
            color: #1B2A4A !important;
        }
        .stTextInput input:focus {
            border-color: #1B2A4A !important;
            box-shadow: 0 0 0 3px rgba(27,42,74,0.12) !important;
            background: #ffffff !important;
            color: #1B2A4A !important;
        }
        .stTextInput input::placeholder {
            color: #A8B8D0 !important;
        }
        /* Labels dos inputs */
        .stTextInput label, .stTextInput label p {
            color: #4A5568 !important;
            font-weight: 600 !important;
            font-size: 13px !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # ── Centralização com colunas ──────────────────────────────────────────────
    _, col, _ = st.columns([1, 1.1, 1])

    with col:
        # Card container — SEM linhas em branco entre tags (CommonMark fecha bloco HTML em blank lines)
        st.markdown(
            '<div style="background:#ffffff;border-radius:16px;padding:40px 40px 32px 40px;box-shadow:0 20px 60px rgba(0,0,0,0.35);">'
            '<div style="text-align:center;margin-bottom:28px;">'
            '<div style="font-size:28px;font-weight:900;color:#1B2A4A;letter-spacing:-0.5px;line-height:1;">AÇO CEARENSE</div>'
            '<div style="font-size:12px;color:#9EA8B3;letter-spacing:2px;text-transform:uppercase;margin-top:4px;">S&OE — Inteligência Comercial</div>'
            '<div style="width:48px;height:3px;background:linear-gradient(90deg,#D96B2D,#E88A4E);border-radius:2px;margin:12px auto 0 auto;"></div>'
            '</div>'
            '<div style="font-size:14px;font-weight:600;color:#1B2A4A;margin-bottom:20px;text-align:center;">Acesso Restrito — Equipe Interna</div>'
            '</div>',
            unsafe_allow_html=True,
        )

        # ── Mensagem de bloqueio / erro ────────────────────────────────────────
        if _is_locked():
            locked_until = st.session_state.get(_K_LOCKED)
            remaining = max(0, int((locked_until - datetime.now()).total_seconds() / 60) + 1)
            st.error(
                f"🔒 Acesso temporariamente bloqueado após {_MAX_ATTEMPTS} tentativas "
                f"incorretas. Tente novamente em {remaining} minuto(s).",
                icon=None,
            )
            return

        error_msg = st.session_state.pop("_login_error_msg", None)
        if error_msg:
            st.error(error_msg)

        # ── Formulário ────────────────────────────────────────────────────────
        with st.form("_auth_login_form", clear_on_submit=False):
            login_input = st.text_input(
                "E-mail ou usuário",
                placeholder="seu.nome@acocearense.com.br",
                key="_auth_login_input",
            )
            pwd_input = st.text_input(
                "Senha",
                type="password",
                placeholder="••••••••",
                key="_auth_pwd_input",
            )
            submitted = st.form_submit_button(
                "Entrar →",
                use_container_width=True,
            )

        # ── Processamento do submit ────────────────────────────────────────────
        if submitted:
            if not login_input or not pwd_input:
                st.session_state["_login_error_msg"] = "Preencha e-mail e senha."
                st.rerun()

            user = _find_user(login_input, pwd_input)
            if user:
                st.session_state[_K_OK]   = True
                st.session_state[_K_USER] = user
                _reset_attempts()
                st.rerun()
            else:
                _register_failed_attempt()
                attempts_left = max(0, _MAX_ATTEMPTS - st.session_state.get(_K_ATTEMPTS, 0))
                if attempts_left > 0:
                    st.session_state["_login_error_msg"] = (
                        f"E-mail ou senha incorretos. "
                        f"({attempts_left} tentativa(s) restante(s) antes do bloqueio)"
                    )
                st.rerun()

        # Rodapé discreto
        st.markdown(
            '<div style="text-align:center;margin-top:16px;font-size:11px;color:#B0BAC9;">'
            'Acesso exclusivo para colaboradores da Aço Cearense.<br>'
            'Em caso de problemas, contate o setor de TI.'
            '</div>',
            unsafe_allow_html=True,
        )
