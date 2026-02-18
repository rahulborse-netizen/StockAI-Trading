"""
OpenAPI/Swagger Documentation
API documentation generator for StockAI Trading Platform
"""
from flask import jsonify
import os

def generate_openapi_spec():
    """Generate OpenAPI 3.0 specification"""
    return {
        "openapi": "3.0.0",
        "info": {
            "title": "StockAI Trading Platform API",
            "version": os.getenv('API_VERSION', 'v1'),
            "description": "AI-powered trading platform API with real-time signals, order management, and portfolio analytics",
            "contact": {
                "name": "StockAI Support"
            }
        },
        "servers": [
            {
                "url": "http://localhost:5000",
                "description": "Development server"
            },
            {
                "url": "https://api.stockai.com",
                "description": "Production server"
            }
        ],
        "paths": {
            "/api/v1/health": {
                "get": {
                    "summary": "Health Check",
                    "description": "Check system health and service status",
                    "tags": ["System"],
                    "responses": {
                        "200": {
                            "description": "System is healthy",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/HealthResponse"
                                    }
                                }
                            }
                        },
                        "503": {
                            "description": "System is degraded"
                        }
                    }
                }
            },
            "/api/v1/signals/{ticker}": {
                "get": {
                    "summary": "Get Trading Signal",
                    "description": "Get AI-generated trading signal for a ticker",
                    "tags": ["Signals"],
                    "parameters": [
                        {
                            "name": "ticker",
                            "in": "path",
                            "required": True,
                            "schema": {
                                "type": "string"
                            },
                            "description": "Stock ticker symbol (e.g., RELIANCE.NS, ^NSEI)"
                        },
                        {
                            "name": "elite",
                            "in": "query",
                            "schema": {
                                "type": "boolean",
                                "default": True
                            },
                            "description": "Use ELITE AI system"
                        },
                        {
                            "name": "refresh",
                            "in": "query",
                            "schema": {
                                "type": "boolean",
                                "default": False
                            },
                            "description": "Force refresh (bypass cache)"
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Signal generated successfully",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/SignalResponse"
                                    }
                                }
                            }
                        },
                        "429": {
                            "description": "Rate limit exceeded"
                        }
                    }
                }
            },
            "/api/v1/realtime-signals/{ticker}": {
                "get": {
                    "summary": "Get Real-Time Signal",
                    "description": "Get real-time updated signal with live price",
                    "tags": ["Signals"],
                    "parameters": [
                        {
                            "name": "ticker",
                            "in": "path",
                            "required": True,
                            "schema": {
                                "type": "string"
                            }
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Real-time signal",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/SignalResponse"
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },
        "components": {
            "schemas": {
                "HealthResponse": {
                    "type": "object",
                    "properties": {
                        "ok": {
                            "type": "boolean"
                        },
                        "status": {
                            "type": "string"
                        },
                        "timestamp": {
                            "type": "string",
                            "format": "date-time"
                        },
                        "version": {
                            "type": "string"
                        },
                        "services": {
                            "type": "object"
                        }
                    }
                },
                "SignalResponse": {
                    "type": "object",
                    "properties": {
                        "ticker": {
                            "type": "string"
                        },
                        "signal": {
                            "type": "string",
                            "enum": ["STRONG_BUY", "BUY", "HOLD", "SELL", "STRONG_SELL"]
                        },
                        "probability": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 1
                        },
                        "confidence": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 1
                        },
                        "current_price": {
                            "type": "number"
                        },
                        "entry_price": {
                            "type": "number"
                        },
                        "stop_loss": {
                            "type": "number"
                        },
                        "target_1": {
                            "type": "number"
                        },
                        "target_2": {
                            "type": "number"
                        },
                        "timestamp": {
                            "type": "string",
                            "format": "date-time"
                        }
                    }
                }
            },
            "securitySchemes": {
                "BearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT"
                }
            }
        }
    }

def register_openapi_routes(app):
    """Register OpenAPI documentation routes"""
    @app.route('/api/docs')
    @app.route('/api/v1/docs')
    def api_docs():
        """API documentation endpoint"""
        spec = generate_openapi_spec()
        return jsonify(spec)
    
    @app.route('/api/swagger.json')
    @app.route('/api/v1/swagger.json')
    def swagger_json():
        """Swagger JSON endpoint"""
        spec = generate_openapi_spec()
        return jsonify(spec)
