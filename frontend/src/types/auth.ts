
export type Role = 'user' | 'admin'

export interface User {
    id: string;
    email: string;
    role: Role;
}

export interface LoginRequest {
    email: string;
    password: string;
}

export interface RegisterRequest {
    email: string;
    password: string;
}
