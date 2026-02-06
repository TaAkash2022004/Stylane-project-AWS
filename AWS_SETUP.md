# AWS Setup Guide for StyleLane

To run `app_aws.py`, you must set up the following resources in your AWS account (Region: `us-east-1`).

## 1. DynamoDB Tables
Create the following tables with the specified **Partition Key**:

| Table Name | Partition Key | Key Type |
|------------|---------------|----------|
| `StyleLaneUsers` | `username` | String |
| `StyleLaneStores` | `store_id` | String |
| `StyleLaneProducts` | `product_id` | String |
| `StyleLaneSales` | `sale_id` | String |
| `StyleLaneRestockRequests` | `restock_request_id` | String |
| `StyleLaneShipments` | `shipment_id` | String |

### Indexes (Optional but Recommended)
For better performance, create Global Secondary Indexes (GSI):
- **StyleLaneProducts**: GSI `StoreIdIndex` on `store_id`
- **StyleLaneSales**: GSI `StoreIdIndex` on `store_id`
- **StyleLaneRestockRequests**: GSI `StoreIdIndex` on `store_id`

## 2. SNS Topic
1. Go to Amazon SNS.
2. Create a Standard Topic named `StyleLaneNotifications`.
3. Copy the **ARN** (e.g., `arn:aws:sns:us-east-1:123456789012:StyleLaneNotifications`).
4. Update the `SNS_TOPIC_ARN` variable in `app_aws.py` with your ARN.

## 3. IAM Role (for EC2)
If running on EC2, attach an IAM Role with these permissions:
- `AmazonDynamoDBFullAccess`
- `AmazonSNSFullAccess`

## 4. Run the App
```bash
pip install boto3 botocore
python app_aws.py
```
