
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
    register(data: RegisterRequest): Promise<User> {
        return request<User>('/register', {
            method: 'POST',
            body: JSON.stringify(data),
        });
    },

    login(data: LoginRequest): Promise<User> {
        return request<User>('/login', {
            method: 'POST',
            body: JSON.stringify(data),
        });
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
