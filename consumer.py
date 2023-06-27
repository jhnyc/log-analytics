import argparse
from pyspark.sql import SparkSession
from pyspark.sql.functions import split
from transformation import split_columns


def transfer(input_df):
    # split columns
    df = split_to_df(input_df, ts_pattern2)
    # check missing values
    # if count_null(df) > 0:
    #     print('Found missing values')
    # format timestamp
    df = format_timestamp(df)
    df_404 = (df.filter(df['status'] == 404))
    status_day_df = df_404.select(df.endpoint, df.time,
                             F.dayofweek('time').alias('weekday'))
    status_freq_df = (status_day_df
                     .withWatermark("time", "1 minutes")
                     .groupBy('weekday', 'time')
                     .count())
    # error_by_day = error_count_by_day(df)
    return status_freq_df

def main(kafka_bootstrap_servers, kafka_topic):
    # Set up Spark session
    spark = SparkSession.builder.appName("KafkaSparkStreaming")\
        .config("spark.sql.streaming.checkpointLocation", "checkpoint")\
        .getOrCreate()

    df = spark \
        .readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", kafka_bootstrap_servers) \
        .option("subscribe", kafka_topic) \
        .option("startingOffsets", "earliest") \
        .load()

    # Select only the `value` column
    df = df.selectExpr("CAST(value AS STRING)")

    # Transform the dataframe
    df = transfer(df)

    # Start the streaming query and write the data to a text file
    query = df.writeStream \
        .format("csv") \
        .option("header", "true") \
        .outputMode("append") \
        .option("checkpointLocation", "checkpoint") \
        .option("path", "output") \
        .outputMode("append") \
        .start()

    # Wait for the query to terminate
    query.awaitTermination()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Kafka Spark Streaming")
    parser.add_argument("--bootstrap-servers", type=str,
                        default="localhost:9092", help="Kafka bootstrap servers")
    parser.add_argument("--topic", type=str,
                        default="kafka_test", help="Kafka topic name")
    args = parser.parse_args()

    main(args.bootstrap_servers, args.topic)
