// cart.js
const BACKEND_URL_ROOT = 'http://127.0.0.1:5500';

/**
 * Sends cart update information to the Python backend and refreshes the local display.
 */
function updateCart(itemName, price, quantity) {
    fetch(`${BACKEND_URL_ROOT}/add_to_cart`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            name: itemName,
            price: price,
            quantity: quantity
        }),
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`Server returned status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        console.log('Cart Update Success:', data);
        // Refresh all counters on the page after a successful update
        loadQuantities(); 
    })
    .catch((error) => {
        console.error('Error updating cart:', error);
        // In a real scenario, you'd show a non-alert message here
    });
}

/**
 * Fetches the current cart state from the backend and updates all relevant item counters on the page.
 */
function loadQuantities() {
    fetch(`${BACKEND_URL_ROOT}/get_cart`)
        .then(response => {
            if (!response.ok) {
                // If backend is not available (404/500), just log error and proceed with zero counts
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(cartData => {
            // Convert array of cart items into a map for fast lookup: { "Item Name": 3, "Other Item": 1, ... }
            const quantityMap = {};
            cartData.forEach(item => {
                // Ensure name is standardized and quantity is a number
                quantityMap[item.name.trim()] = parseInt(item.quantity) || 0;
            });

            // Iterate over all counter display elements on the page
            const counterDisplays = document.querySelectorAll('.counter-display');
            
            counterDisplays.forEach(displayElement => {
                const itemName = displayElement.getAttribute('data-item-name');
                if (itemName) {
                    // Get the quantity from the map, defaulting to 0
                    const quantity = quantityMap[itemName.trim()] || 0;
                    displayElement.innerText = quantity;
                }
            });
        })
        .catch(error => {
            console.error("Failed to load initial quantities:", error);
            // On failure, set all counters to 0
            document.querySelectorAll('.counter-display').forEach(el => el.innerText = '0');
        });
}


function increase(counterId, itemName, price) {
    // We don't read the DOM for current quantity anymore; loadQuantities will update it after backend confirms
    const currentDisplay = document.querySelector(`#${counterId} .counter-display`);
    let currentQuantity = parseInt(currentDisplay.innerText) || 0;
    let newQuantity = currentQuantity + 1;
    
    // Call the function to update the backend
    updateCart(itemName, price, newQuantity);
}

function decrease(counterId, itemName, price) {
    // We don't read the DOM for current quantity anymore; loadQuantities will update it after backend confirms
    const currentDisplay = document.querySelector(`#${counterId} .counter-display`);
    let currentQuantity = parseInt(currentDisplay.innerText) || 0;
    
    if (currentQuantity > 0) {
        let newQuantity = currentQuantity - 1;
        // Call the function to update the backend
        updateCart(itemName, price, newQuantity);
    }
}

// Add event listener to load quantities once the window is fully loaded
window.addEventListener('load', loadQuantities);
