from src.models.app_event import AppEvent
from src.models.user_setup import UserSetup
from datetime import datetime, timedelta
from bson.objectid import ObjectId

def get_app_metrics(app_id):
    app_obj_id = ObjectId(app_id)
    
    registrations = AppEvent.collection.count_documents({
        "app_id": app_obj_id,
        "event_type": "registration",
        "status": "success"
    })

    successful_transactions = AppEvent.collection.count_documents({
        "app_id": app_obj_id,
        "event_type": "transaction",
        "status": "success",
        "message": {"$nin": ["Off-ramp"]}
    })
    failed_transactions = AppEvent.collection.count_documents({
        "app_id": app_obj_id,
        "event_type": "transaction",
        "status": "failed",
        "message": {"$nin": ["Off-ramp"]}
    })
    off_ramps = AppEvent.collection.count_documents({
        "app_id": app_obj_id,
        "event_type": "off_ramp",
        "status": "success"
    })

    balance_checks = AppEvent.collection.count_documents({
        "app_id": app_obj_id,
        "event_type": "balance_check",
        "status": "success"
    })

    one_day_ago = datetime.utcnow() - timedelta(days=1)
    daily_active_users_query = AppEvent.collection.aggregate([
        {"$match": {"app_id": app_obj_id, "timestamp": {"$gte": one_day_ago}}},
        {"$group": {"_id": "$phone_number"}},
        {"$count": "count"}
    ])
    daily_active_users = next(daily_active_users_query, {"count": 0})["count"]

    endpoint_calls_query = AppEvent.collection.aggregate([
        {"$match": {"app_id": app_obj_id, "event_type": {"$in": ["verify_endpoint", "send_crypto", "off_ramp", "balance_check", "external_app_forward"]}, "timestamp": {"$gte": one_day_ago}}},
        {"$group": {
            "_id": "$event_type",
            "total_calls": {"$sum": 1},
            "successful_calls": {"$sum": {"$cond": [{"$eq": ["$status", "success"]}, 1, 0]}},
            "avg_latency_ms": {"$avg": "$latency_ms"}
        }}
    ])
    endpoint_metrics = {item['_id']: {
        'total_calls': item['total_calls'],
        'successful_calls': item['successful_calls'],
        'failure_rate': (1 - item['successful_calls'] / item['total_calls']) * 100 if item['total_calls'] > 0 else 0,
        'avg_latency_ms': round(item['avg_latency_ms'], 2) if item['avg_latency_ms'] is not None else None
    } for item in endpoint_calls_query}

    total_user_setups = UserSetup.collection.count_documents({"app_id": app_obj_id})


    return {
        "app_id": app_id,
        "registrations": registrations,
        "transactions": {
            "successful": successful_transactions,
            "failed": failed_transactions,
            "off_ramps": off_ramps
        },
        "balance_checks": balance_checks,
        "usage": {
            "daily_active_users_24h": daily_active_users
        },
        "system_endpoint_metrics_24h": endpoint_metrics,
        "total_user_setups": total_user_setups
    }