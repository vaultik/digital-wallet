# tests/integration/test_auth_api.py
from http import HTTPStatus

import pytest
from httpx import AsyncClient


# Register
async def test_register_success(
        async_client: AsyncClient,
        test_user: dict
):
    """Successful registration returns 201 and access token."""
    response = await async_client.post(
        '/api/v1/auth/register',
        json=test_user
    )
    assert response.status_code == HTTPStatus.CREATED
    data = response.json()
    assert 'access_token' in data
    assert data['token_type'] == 'Bearer'
    assert 'refresh_token' in response.cookies


async def test_register_duplicate_username(
        async_client: AsyncClient,
        test_user: dict
):
    """Registering with existing username returns 409."""
    await async_client.post('/api/v1/auth/register', json=test_user)
    response = await async_client.post(
        '/api/v1/auth/register',
        json=test_user
    )
    assert response.status_code == HTTPStatus.CONFLICT


# Login
async def test_login_success(
        async_client: AsyncClient,
        test_user: dict
):
    """Successful login returns 200 and access token."""
    await async_client.post('/api/v1/auth/register', json=test_user)
    response = await async_client.post(
        '/api/v1/auth/login',
        json=test_user
    )
    assert response.status_code == HTTPStatus.OK
    assert 'access_token' in response.json()


async def test_login_wrong_password(
        async_client: AsyncClient,
        test_user: dict,
        wrong_password_user: dict
):
    """Login with wrong password returns 401 Unauthorized."""
    await async_client.post('/api/v1/auth/register', json=test_user)
    response = await async_client.post(
        '/api/v1/auth/login',
        json=wrong_password_user
    )
    assert response.status_code == HTTPStatus.UNAUTHORIZED


async def test_login_user_not_found(
        async_client: AsyncClient,
        nonexistent_user: dict
):
    """Login with non-existent username returns 401 Unauthorized."""
    response = await async_client.post(
        '/api/v1/auth/login',
        json=nonexistent_user
    )
    assert response.status_code == HTTPStatus.UNAUTHORIZED


# Refresh
async def test_refresh_success(
        async_client: AsyncClient,
        test_user: dict
):
    """Refresh returns 200 and new access token when valid cookie is present."""
    await async_client.post('/api/v1/auth/register', json=test_user)
    await async_client.post('/api/v1/auth/login', json=test_user)

    response = await async_client.post('/api/v1/auth/refresh')
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert 'access_token' in data
    assert data['token_type'] == 'Bearer'
    assert data['expires_in'] == 900


async def test_refresh_without_cookie(async_client:AsyncClient):
    """Refresh without cookie returns 401 Unauthorized."""
    response = await async_client.post('/api/v1/auth/refresh')
    assert response.status_code == HTTPStatus.UNAUTHORIZED


# Logout
async def test_logout_success(
        async_client: AsyncClient,
        test_user: dict
):
    """Logout returns 204 No Content and clears refresh token cookie."""
    await async_client.post('/api/v1/auth/register', json=test_user)
    response = await async_client.post('/api/v1/auth/login', json=test_user)
    assert response.status_code == HTTPStatus.OK
    response = await async_client.post('/api/v1/auth/logout')
    assert response.status_code == HTTPStatus.NO_CONTENT
