
import type {
    User,
    LoginRequest,
    RegisterRequest,
} from '../types/auth';

const AUTH_URL = '/api/auth';

export class AuthApiError extends Error {
    readonly status: number;

    constructor(message: string, status: number) {
        super(message);
        this.name = 'AuthApiError';
        this.status = status;
    }
}

async function request<T>(
    endpoint: string,
    options: RequestInit = {},
): Promise<T> {
    const response = await fetch(`${AUTH_URL}${endpoint}`, {
        ...options,
        credentials: 'include',
        headers: {
            'Content-Type': 'application/json',
            ...options.headers,
        },
    });

    if (!response.ok) {
        const body = await response.json().catch(() => null);

        throw new AuthApiError(
            typeof body?.detail === 'string'
                ? body.detail
                : 'An unexpected error occurred.',
            response.status,
        );
    }

    if (response.status === 204) {
        return undefined as T;
    }

    return response.json() as Promise<T>;
}

export const authApi = {
    // The backend does not create a session on register (no Set-Cookie), so
    // log in right away to establish the session the rest of the app needs.
    register(data: RegisterRequest): Promise<User> {
        return request<User>('/register', {
            method: 'POST',
            body: JSON.stringify(data),
        }).then(() =>
            authApi.login({ email: data.email, password: data.password }),
        );
    },

    // The backend returns { token, user } (and sets the session cookie); the
    // cookie carries the session, so only the user is used.
    login(data: LoginRequest): Promise<User> {
        return request<{ token: string; user: User }>('/login', {
            method: 'POST',
            body: JSON.stringify(data),
        }).then((data) => data.user);
    },

    getCurrentUser(): Promise<User> {
        return request<User>('/me', {
            method: 'GET',
        });
    },

    logout(): Promise<void> {
        return request<void>('/logout', {
            method: 'POST',
        });
    },
};
