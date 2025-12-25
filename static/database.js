
// Canteen Database API Client
window.CanteenDB = {
    // Fetch menu items from the backend API
    async getFoodItems() {
        try {
            const response = await fetch('/api/menu');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const items = await response.json();
            console.log('Menu items fetched:', items);
            return items;
        } catch (error) {
            console.error('Error fetching menu items:', error);
            return [];
        }
    },

    // Place an order
    async saveOrder(orderData) {
        try {
            const response = await fetch('/api/orders/place', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(orderData)
            });

            if (!response.ok) {
                const errorData = await response.json();
                console.error('Order failed:', errorData);
                throw new Error(errorData.error || 'Failed to place order');
            }

            const result = await response.json();
            console.log('Order placed successfully:', result);
            return result.orderId;
        } catch (error) {
            console.error('Error placing order:', error);
            throw error;
        }
    },

    // Get all orders (staff only)
    async getOrders() {
        try {
            const response = await fetch('/api/orders', {
                method: 'GET',
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            if (!response.ok) {
                console.error(`API Error: ${response.status}`);
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            console.log(`✓ Orders loaded: ${(data.orders || []).length} orders`);
            return data.orders || [];
        } catch (error) {
            console.error('Error fetching orders:', error);
            return [];
        }
    },

    // Get all orders as array (staff only)
    async getAllOrdersArray() {
        try {
            const response = await fetch('/api/orders', {
                method: 'GET',
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            if (!response.ok) {
                console.error(`API Error: ${response.status}`);
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            console.log(`✓ Orders loaded: ${(data.orders || []).length} orders`);
            return data.orders || [];
        } catch (error) {
            console.error('Error fetching orders:', error);
            return [];
        }
    },

    // Update order status (staff only)
    async updateOrderStatus(orderId, status) {
        try {
            const response = await fetch('/api/orders/update_status', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ orderId, status })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result = await response.json();
            return result.success;
        } catch (error) {
            console.error('Error updating order status:', error);
            return false;
        }
    },

    // Update menu item sold out status (staff only)
    async updateMenuItem(itemId, soldOut) {
        try {
            const response = await fetch('/api/menu/update', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ itemId, soldOut })
            });

            if (!response.ok) {
                const errorData = await response.json();
                console.error('Menu update failed:', errorData);
                throw new Error(errorData.error || 'Failed to update menu');
            }

            const result = await response.json();
            return result.status === 'success';
        } catch (error) {
            console.error('Error updating menu item:', error);
            return false;
        }
    },

    // Clear session (logout)
    clearSession() {
        sessionStorage.removeItem('currentUser');
        window.location.href = '/logout';
    },

    // Get current session
    getSession() {
        const userStr = sessionStorage.getItem('currentUser');
        if (userStr) {
            try {
                return JSON.parse(userStr);
            } catch (e) {
                console.error('Error parsing session:', e);
                return null;
            }
        }
        return null;
    },

    // Save user session
    saveSession(userData) {
        sessionStorage.setItem('currentUser', JSON.stringify(userData));
    }
};

console.log('CanteenDB loaded successfully');
