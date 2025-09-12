const axios = require('axios');

// DOUANO API Configuration
const DOUANO_CONFIG = {
    'client_id': '3',
    'client_secret': 'KBPJZ11EwPjAmEUKFWDoXGQaDdMRPFES2P6VCxEC',
    'base_url': 'https://yugen.douano.com',
    'auth_url': 'https://yugen.douano.com/authorize',
    'token_url': 'https://yugen.douano.com/oauth/token',
    'redirect_uri': 'https://verdant-faloodeh-8eb16e.netlify.app/oauth/callback'
};

// Helper function to make paginated API requests
async function makePaginatedApiRequest(endpoint, token, params = {}) {
    const allData = [];
    let currentPage = 1;
    const perPage = 100;
    
    while (true) {
        const response = await axios.get(`${DOUANO_CONFIG.base_url}${endpoint}`, {
            headers: {
                'Authorization': `Bearer ${token}`,
                'Accept': 'application/json'
            },
            params: {
                ...params,
                per_page: perPage,
                page: currentPage
            }
        });
        
        const data = response.data;
        if (data.result && data.result.data) {
            allData.push(...data.result.data);
            
            const currentPageNum = data.result.current_page || 1;
            const lastPage = data.result.last_page || 1;
            
            if (currentPageNum >= lastPage) {
                break;
            }
            currentPage += 1;
        } else {
            return data;
        }
    }
    
    return {
        result: {
            data: allData,
            total: allData.length,
            current_page: 1,
            last_page: 1,
            per_page: allData.length
        }
    };
}

exports.handler = async (event, context) => {
    // Enable CORS
    const headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization',
        'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS'
    };

    // Handle preflight requests
    if (event.httpMethod === 'OPTIONS') {
        return {
            statusCode: 200,
            headers,
            body: ''
        };
    }

    try {
        const path = event.path.replace('/.netlify/functions/api', '');
        console.log('Function called with path:', event.path, 'cleaned path:', path);
        console.log('Query parameters:', event.queryStringParameters);
        
        // Route handling with comprehensive API support
        if (path === '/oauth/authorize') {
            return handleOAuthAuthorize(event, headers);
        } else if (path === '/oauth/callback') {
            return handleOAuthCallback(event, headers);
        } else if (path === '/api/companies') {
            return handleCompaniesAPI(event, headers);
        } else if (path === '/api/sales' || path === '/api/sales-invoices') {
            return handleSalesAPI(event, headers);
        } else if (path === '/api/products' || path === '/api/products/hierarchy') {
            return handleProductsAPI(event, headers);
        } else if (path.startsWith('/api/composed-product-items')) {
            return handleComposedProductItemsAPI(event, headers);
        } else if (path.startsWith('/api/company-categories')) {
            return handleCompanyCategoriesAPI(event, headers);
        } else if (path.startsWith('/api/crm-contacts')) {
            return handleCrmContactsAPI(event, headers);
        } else if (path.startsWith('/api/accountancy/')) {
            return handleAccountancyAPI(event, headers);
        } else {
            return {
                statusCode: 404,
                headers,
                body: JSON.stringify({ error: 'Endpoint not found' })
            };
        }
    } catch (error) {
        console.error('API Error:', error);
        return {
            statusCode: 500,
            headers,
            body: JSON.stringify({ error: 'Internal server error' })
        };
    }
};

function handleOAuthAuthorize(event, headers) {
    const authUrl = `${DOUANO_CONFIG.auth_url}?` + new URLSearchParams({
        client_id: DOUANO_CONFIG.client_id,
        redirect_uri: DOUANO_CONFIG.redirect_uri,
        response_type: 'code',
        scope: 'read write'
    });

    return {
        statusCode: 302,
        headers: {
            ...headers,
            'Location': authUrl
        },
        body: ''
    };
}

async function handleOAuthCallback(event, headers) {
    const { code } = event.queryStringParameters || {};
    
    if (!code) {
        return {
            statusCode: 302,
            headers: {
                ...headers,
                'Location': '/?error=no_code'
            },
            body: ''
        };
    }

    try {
        console.log('Attempting token exchange with:', {
            client_id: DOUANO_CONFIG.client_id,
            redirect_uri: DOUANO_CONFIG.redirect_uri,
            code: code ? 'present' : 'missing'
        });

        const tokenResponse = await axios.post(DOUANO_CONFIG.token_url, {
            client_id: DOUANO_CONFIG.client_id,
            client_secret: DOUANO_CONFIG.client_secret,
            code: code,
            grant_type: 'authorization_code',
            redirect_uri: DOUANO_CONFIG.redirect_uri
        });

        // Redirect back to main page with token as query parameter
        const redirectUrl = `/?token=${encodeURIComponent(tokenResponse.data.access_token)}`;
        
        return {
            statusCode: 302,
            headers: {
                ...headers,
                'Location': redirectUrl
            },
            body: ''
        };
    } catch (error) {
        console.error('OAuth token exchange error:', error.response?.data || error.message);
        return {
            statusCode: 302,
            headers: {
                ...headers,
                'Location': '/?error=token_exchange_failed'
            },
            body: ''
        };
    }
}

async function handleCompaniesAPI(event, headers) {
    const authHeader = event.headers.authorization;
    if (!authHeader) {
        return {
            statusCode: 401,
            headers,
            body: JSON.stringify({ error: 'Authorization header required' })
        };
    }

    const token = authHeader.replace('Bearer ', '');
    const params = event.queryStringParameters || {};
    
    try {
        // Handle lightweight search for typeahead
        const searchQ = params.q;
        if (searchQ) {
            const data = await makePaginatedApiRequest('/api/public/v1/core/companies', token, {
                filter: searchQ,
                per_page: params.per_page || 50
            });
            
            if (data.result && data.result.data) {
                // Normalize to minimal payload for dropdown
                const results = data.result.data;
                const minimal = results.map(c => ({
                    id: c.id,
                    name: c.public_name || c.name || ''
                }));
                
                return {
                    statusCode: 200,
                    headers,
                    body: JSON.stringify({ result: { data: minimal } })
                };
            }
        }

        // Regular companies API call with full data
        const data = await makePaginatedApiRequest('/api/public/v1/core/companies', token, params);

        return {
            statusCode: 200,
            headers,
            body: JSON.stringify(data)
        };
    } catch (error) {
        console.error('Companies API error:', error.response?.data || error.message);
        return {
            statusCode: error.response?.status || 500,
            headers,
            body: JSON.stringify({ error: 'Failed to fetch companies data' })
        };
    }
}

async function handleSalesAPI(event, headers) {
    const authHeader = event.headers.authorization;
    if (!authHeader) {
        return {
            statusCode: 401,
            headers,
            body: JSON.stringify({ error: 'Authorization header required' })
        };
    }

    const token = authHeader.replace('Bearer ', '');
    const params = event.queryStringParameters || {};
    
    try {
        // Set up parameters for sales invoices API
        const apiParams = {
            per_page: 100,
            page: 1
        };

        // Add filtering parameters from query string
        if (params.filter_by_created_since) apiParams.filter_by_created_since = params.filter_by_created_since;
        if (params.filter_by_updated_since) apiParams.filter_by_updated_since = params.filter_by_updated_since;
        if (params.filter_by_start_date) apiParams.filter_by_start_date = params.filter_by_start_date;
        if (params.filter_by_end_date) apiParams.filter_by_end_date = params.filter_by_end_date;
        if (params.filter_by_company) apiParams.filter_by_company = params.filter_by_company;
        if (params.filter_by_status) apiParams.filter_by_status = params.filter_by_status;
        if (params.order_by_date) apiParams.order_by_date = params.order_by_date;
        if (params.order_by_amount) apiParams.order_by_amount = params.order_by_amount;

        const data = await makePaginatedApiRequest('/api/public/v1/trade/sales-invoices', token, apiParams);

        return {
            statusCode: 200,
            headers,
            body: JSON.stringify(data)
        };
    } catch (error) {
        console.error('Sales API error:', error.response?.data || error.message);
        return {
            statusCode: error.response?.status || 500,
            headers,
            body: JSON.stringify({ error: 'Failed to fetch sales data' })
        };
    }
}

async function handleProductsAPI(event, headers) {
    const authHeader = event.headers.authorization;
    if (!authHeader) {
        return {
            statusCode: 401,
            headers,
            body: JSON.stringify({ error: 'Authorization header required' })
        };
    }

    const token = authHeader.replace('Bearer ', '');
    
    try {
        // Get all composed product items with pagination
        const data = await makePaginatedApiRequest('/api/public/v1/core/composed-product-items', token, {
            'per_page': 100,
            'page': 1
        });
        
        if (data.result && data.result.data) {
            const items = data.result.data;
            
            // Process the data to create a hierarchical structure (like Flask version)
            const hierarchy = {};
            const uniqueProducts = {};
            
            for (const item of items) {
                const composedProduct = item.composed_product || {};
                const componentProduct = item.product || {};
                const quantity = item.quantity || 0;
                
                // Track unique products
                if (composedProduct.id) {
                    uniqueProducts[composedProduct.id] = {
                        ...composedProduct,
                        type: 'composed'
                    };
                }
                if (componentProduct.id) {
                    uniqueProducts[componentProduct.id] = {
                        ...componentProduct,
                        type: 'component'
                    };
                }
                
                const composedId = composedProduct.id;
                if (!hierarchy[composedId]) {
                    hierarchy[composedId] = {
                        composed_product: composedProduct,
                        components: [],
                        total_components: 0
                    };
                }
                
                hierarchy[composedId].components.push({
                    product: componentProduct,
                    quantity: quantity,
                    item_id: item.id,
                    created_at: item.created_at,
                    updated_at: item.updated_at
                });
                hierarchy[composedId].total_components += 1;
            }
            
            // Convert to list format and add statistics
            const hierarchyList = Object.values(hierarchy);
            
            // Add summary statistics
            const result = {
                result: {
                    data: items,
                    hierarchy: hierarchyList,
                    statistics: {
                        total_composed_products: hierarchyList.length,
                        total_unique_products: Object.keys(uniqueProducts).length,
                        total_component_relationships: items.length
                    },
                    unique_products: Object.values(uniqueProducts)
                }
            };
            
            return {
                statusCode: 200,
                headers,
                body: JSON.stringify(result)
            };
        }

        return {
            statusCode: 200,
            headers,
            body: JSON.stringify(data)
        };
    } catch (error) {
        console.error('Products API error:', error.response?.data || error.message);
        return {
            statusCode: error.response?.status || 500,
            headers,
            body: JSON.stringify({ error: 'Failed to fetch products data' })
        };
    }
}

// New handler for composed product items
async function handleComposedProductItemsAPI(event, headers) {
    const authHeader = event.headers.authorization;
    if (!authHeader) {
        return {
            statusCode: 401,
            headers,
            body: JSON.stringify({ error: 'Authorization header required' })
        };
    }

    const token = authHeader.replace('Bearer ', '');
    
    try {
        const data = await makePaginatedApiRequest('/api/public/v1/core/composed-product-items', token, event.queryStringParameters || {});

        return {
            statusCode: 200,
            headers,
            body: JSON.stringify(data)
        };
    } catch (error) {
        console.error('Composed Product Items API error:', error.response?.data || error.message);
        return {
            statusCode: error.response?.status || 500,
            headers,
            body: JSON.stringify({ error: 'Failed to fetch composed product items' })
        };
    }
}

// New handler for company categories
async function handleCompanyCategoriesAPI(event, headers) {
    const authHeader = event.headers.authorization;
    if (!authHeader) {
        return {
            statusCode: 401,
            headers,
            body: JSON.stringify({ error: 'Authorization header required' })
        };
    }

    const token = authHeader.replace('Bearer ', '');
    
    try {
        const data = await makePaginatedApiRequest('/api/public/v1/core/company-categories', token, event.queryStringParameters || {});

        return {
            statusCode: 200,
            headers,
            body: JSON.stringify(data)
        };
    } catch (error) {
        console.error('Company Categories API error:', error.response?.data || error.message);
        return {
            statusCode: error.response?.status || 500,
            headers,
            body: JSON.stringify({ error: 'Failed to fetch company categories' })
        };
    }
}

// New handler for CRM contacts
async function handleCrmContactsAPI(event, headers) {
    const authHeader = event.headers.authorization;
    if (!authHeader) {
        return {
            statusCode: 401,
            headers,
            body: JSON.stringify({ error: 'Authorization header required' })
        };
    }

    const token = authHeader.replace('Bearer ', '');
    
    try {
        const data = await makePaginatedApiRequest('/api/public/v1/crm/crm-contact-persons', token, event.queryStringParameters || {});

        return {
            statusCode: 200,
            headers,
            body: JSON.stringify(data)
        };
    } catch (error) {
        console.error('CRM Contacts API error:', error.response?.data || error.message);
        return {
            statusCode: error.response?.status || 500,
            headers,
            body: JSON.stringify({ error: 'Failed to fetch CRM contacts' })
        };
    }
}

// New handler for accountancy endpoints
async function handleAccountancyAPI(event, headers) {
    const authHeader = event.headers.authorization;
    if (!authHeader) {
        return {
            statusCode: 401,
            headers,
            body: JSON.stringify({ error: 'Authorization header required' })
        };
    }

    const token = authHeader.replace('Bearer ', '');
    const path = event.path.replace('/.netlify/functions/api', '');
    
    try {
        let endpoint = '';
        if (path.includes('/accounts')) {
            endpoint = '/api/public/v1/accountancy/accounts';
        } else if (path.includes('/bookings')) {
            endpoint = '/api/public/v1/accountancy/bookings';
        } else {
            return {
                statusCode: 404,
                headers,
                body: JSON.stringify({ error: 'Accountancy endpoint not found' })
            };
        }

        const data = await makePaginatedApiRequest(endpoint, token, event.queryStringParameters || {});

        return {
            statusCode: 200,
            headers,
            body: JSON.stringify(data)
        };
    } catch (error) {
        console.error('Accountancy API error:', error.response?.data || error.message);
        return {
            statusCode: error.response?.status || 500,
            headers,
            body: JSON.stringify({ error: 'Failed to fetch accountancy data' })
        };
    }
}
