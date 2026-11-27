
import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from './useAuth';

// Nested inside ProtectedRoute, so the user is already authenticated here.
// Non-admins are sent back home; the backend enforces the same rule (403).
export default function AdminRoute() {
    const { isAdmin } = useAuth();

    if (!isAdmin) {
        return <Navigate to="/" replace />;
    }

    return <Outlet />;
}
