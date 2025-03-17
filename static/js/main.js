// Form validation
document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('payment-form');
    
    if (form) {
        form.addEventListener('submit', function(event) {
            const amount = document.getElementById('amount').value;
            const description = document.getElementById('description').value;
            const email = document.getElementById('email').value;
            const phone = document.getElementById('phone').value;
            
            let isValid = true;
            
            // Basic validation
            if (!amount || amount <= 0) {
                highlightError('amount', 'Please enter a valid amount');
                isValid = false;
            }
            
            if (!description.trim()) {
                highlightError('description', 'Please enter a description');
                isValid = false;
            }
            
            // Email validation
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(email)) {
                highlightError('email', 'Please enter a valid email address');
                isValid = false;
            }
            
            // Phone validation
            const phoneRegex = /^\+?[0-9]{10,15}$/;
            if (!phoneRegex.test(phone.replace(/\s+/g, ''))) {
                highlightError('phone', 'Please enter a valid phone number');
                isValid = false;
            }
            
            if (!isValid) {
                event.preventDefault();
            }
        });
    }
    
    // Helper function to highlight errors
    function highlightError(fieldId, message) {
        const field = document.getElementById(fieldId);
        field.style.borderColor = 'var(--danger-color)';
        
        // Create error message
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message';
        errorDiv.textContent = message;
        errorDiv.style.color = 'var(--danger-color)';
        errorDiv.style.fontSize = '0.8rem';
        errorDiv.style.marginTop = '0.25rem';
        
        // Remove any existing error message
        const existingError = field.parentNode.querySelector('.error-message');
        if (existingError) {
            field.parentNode.removeChild(existingError);
        }
        
        // Add the error message
        field.parentNode.appendChild(errorDiv);
        
        // Clear the error when the field is focused
        field.addEventListener('focus', function() {
            this.style.borderColor = 'var(--primary-color)';
            const error = this.parentNode.querySelector('.error-message');
            if (error) {
                this.parentNode.removeChild(error);
            }
        }, { once: true });
    }
});