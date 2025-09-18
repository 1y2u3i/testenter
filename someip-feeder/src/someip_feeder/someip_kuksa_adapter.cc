/********************************************************************************
* Copyright (c) 2022 Contributors to the Eclipse Foundation
*
* See the NOTICE file(s) distributed with this work for additional
* information regarding copyright ownership.
*
* This program and the accompanying materials are made available under the
* terms of the Apache License 2.0 which is available at
* http://www.apache.org/licenses/LICENSE-2.0
*
* SPDX-License-Identifier: Apache-2.0
********************************************************************************/

#include <csignal>
#include <iostream>
#include <sstream>
#include <string>
#include <thread>
#include <unistd.h> // access()
#include <iterator>

#include "someip_kuksa_adapter.h"
#include "data_broker_feeder.h"
#include "create_datapoint.h"

#include "someip_client.h"
#include "wiper_poc.h"

using sdv::databroker::v1::Datapoint;
using sdv::databroker::v1::DataType;
using sdv::databroker::v1::ChangeType;
using sdv::databroker::v1::Datapoint_Failure;


namespace sdv {
namespace adapter {

/*** LOG helpers */
#define LEVEL_TRC   3
#define LEVEL_DBG   2
#define LEVEL_INF   1
#define LEVEL_ERR   0
#define MODULE_PREFIX   "# SomeipFeederAdapter::"

#define LOG_TRACE   if (log_level_ >= LEVEL_TRC) std::cout << MODULE_PREFIX << __func__ << ": [trace] "
#define LOG_DEBUG   if (log_level_ >= LEVEL_DBG) std::cout << MODULE_PREFIX << __func__ << ": [debug] "
#define LOG_INFO    if (log_level_ >= LEVEL_INF) std::cout << MODULE_PREFIX << __func__ << ": [info] "
#define LOG_ERROR   if (log_level_ >= LEVEL_ERR) std::cerr << MODULE_PREFIX << __func__ << ": [error] "

#define SOMEIP_METHOD_PAYLOAD_SIZE     6

SomeipFeederAdapter::SomeipFeederAdapter():
    feeder_active_(false),
    databroker_addr_(),
    databroker_feeder_(nullptr),
    feeder_thread_(nullptr),
    subscriber_thread_(nullptr),
    someip_active_(false),
    someip_thread_(nullptr),
    someip_client_(nullptr),
    someip_use_tcp_(false),
    shutdown_requested_(false)
{
    log_level_ = sdv::someip::getEnvironmentInt("SOMEIP_CLI_DEBUG", 1, false);
}

SomeipFeederAdapter::~SomeipFeederAdapter() {
    LOG_TRACE << "called." << std::endl;
    Shutdown();
    LOG_TRACE << "done." << std::endl;
}


sdv::databroker::v1::DataType SomeipFeederAdapter::getDataType(std::string dataType)
{
    if ((dataType.compare("BOOL") == 0) || (dataType.compare("bool") == 0))
    {
        return  sdv::databroker::v1::DataType::BOOL;
    }
    if ((dataType.compare("STRING") == 0) || (dataType.compare("string") == 0))
    {
        return sdv::databroker::v1::DataType::STRING;
    }
    if ((dataType.compare("FLOAT") == 0) || (dataType.compare("float") == 0))
    {
        return sdv::databroker::v1::DataType::FLOAT;
    }
    if ((dataType.compare("UINT32") == 0) || (dataType.compare("uint32") == 0))
    {
        return sdv::databroker::v1::DataType::UINT32;
    }
    if ((dataType.compare("UINT8") == 0) || (dataType.compare("uint8") == 0))
    {
        return sdv::databroker::v1::DataType::UINT8;
    }
    if ((dataType.compare("INT8") == 0) || (dataType.compare("int8") == 0))
    {
        return sdv::databroker::v1::DataType::INT8;
    }    
    if ((dataType.compare("UINT16") == 0) || (dataType.compare("uint16") == 0))
    {
        return sdv::databroker::v1::DataType::UINT16;
    }
    if ((dataType.compare("INT16") == 0) || (dataType.compare("int16") == 0))
    {
        return sdv::databroker::v1::DataType::INT16;
    }
    if ((dataType.compare("UINT8[]") == 0) || (dataType.compare("uint8[]") == 0))
    {
        return sdv::databroker::v1::DataType::UINT8_ARRAY;
    }
    if ((dataType.compare("UINT16[]") == 0) || (dataType.compare("uint16[]") == 0))
    {
        return sdv::databroker::v1::DataType::UINT16_ARRAY;
    }
    if ((dataType.compare("INT16[]") == 0) || (dataType.compare("int16[]") == 0))
    {
        return sdv::databroker::v1::DataType::INT16_ARRAY;
    }
    if ((dataType.compare("INT8_UINT16") == 0) || (dataType.compare("int8_uint16") == 0))
    {
        return sdv::databroker::v1::DataType::TIMESTAMP_ARRAY; /* Workaround since we cant add custom data type */
    }
    
    /*Default return as string */
    return sdv::databroker::v1::DataType::STRING;
}


bool SomeipFeederAdapter::InitDataBrokerFeeder(const std::string &databroker_addr, const std::string& auth_token,sdv::someip::SomeIPConfig _config) {

sdv::broker_feeder::DatapointConfiguration metadata;
std::vector<std::string> vssActuatorList;
    for (const auto& mapping : _config.VSSMap)
    {
        LOG_INFO<<"JSON Config Service ID " <<std::hex << mapping.metaData.serviceID <<std::endl;
        LOG_INFO<<"JSON Config VSS Node Info "<<mapping.vssNodes.size() <<std::endl;
        if(mapping.metaData.serviceType.compare("Event") == 0)
        {
            for (const auto& node : mapping.vssNodes)
            {
                LOG_INFO<< "Name: " << node.name << ",Data type " <<node.datatype <<", Byte Offset: " << node.byteOffset << ", Length: " << node.length << std::endl;
                sdv::databroker::v1::DataType datatype = getDataType(node.datatype);
                metadata.push_back (sdv::broker_feeder::DatapointMetadata{node.name,datatype,ChangeType::ON_CHANGE,sdv::broker_feeder::createNotAvailableValue(),"No description"});
            }
        }
        else if(mapping.metaData.serviceType.compare("Method") == 0)
        {
            for (const auto& node : mapping.vssNodes)
            {
                vssActuatorList.push_back(node.name);
            }
        }
    }

    LOG_INFO << "Connecting to " << databroker_addr << std::endl;

    // debug: KUKSA_DEBUG
    collector_client_ = sdv::broker_feeder::CollectorClient::createInstance(databroker_addr, auth_token);
    // debug: DBF_DEBUG
    databroker_feeder_ = sdv::broker_feeder::DataBrokerFeeder::createInstance(collector_client_, std::move(metadata));
    // debug: KUKSA_DEBUG
    actuator_subscriber_ = sdv::broker_feeder::kuksa::ActuatorSubscriber::createInstance(collector_client_);
    actuator_subscriber_->Init(vssActuatorList,
        std::bind(&SomeipFeederAdapter::on_actuator_change, this, std::placeholders::_1, _config)
    );

    return true;
}

bool SomeipFeederAdapter::InitSomeipClient(sdv::someip::SomeIPConfig _config) {

    someip_use_tcp_ = _config.use_tcp;

    auto someip_app = ::getenv("VSOMEIP_APPLICATION_NAME");
    auto someip_config = ::getenv("VSOMEIP_CONFIGURATION");

    bool someip_ok = true;
    if (!someip_app) {
        LOG_ERROR << "VSOMEIP_APPLICATION_NAME not set in environment, someip disabled!" << std::endl;
        someip_ok = false;
    }
    if (someip_config == nullptr) {
        LOG_ERROR << "VSOMEIP_CONFIGURATION not set in environment, someip disabled!" << std::endl;
        someip_ok = false;
    } else {
        if (::access(someip_config, F_OK) == -1) {
            LOG_ERROR << "env VSOMEIP_CONFIGURATION file is missing: " << someip_config << std::endl;
            someip_ok = false;
        }
    }

    if (someip_ok) {
        std::stringstream ss;
        ss << "\n"
            << "### VSOMEIP_APPLICATION_NAME=" << someip_app << "\n"
            << "### VSOMEIP_CONFIGURATION=" << someip_config << "\n"
            << "$ cat " << someip_config << std::endl;
        LOG_INFO << ss.str();

        std::string cmd;
        cmd = "cat " + std::string(someip_config);
        int rc = ::system(cmd.c_str());
        std::cout << std::endl;

        someip_client_ = sdv::someip::SomeIPClient::createInstance(
            _config,
            std::bind(&SomeipFeederAdapter::on_someip_message,
                    this, std::placeholders::_1, std::placeholders::_2, std::placeholders::_3, std::placeholders::_4, std::placeholders::_5));
    }
    someip_active_ = someip_ok;
    return someip_ok;
}

void SomeipFeederAdapter::on_actuator_change(sdv::broker_feeder::kuksa::ActuatorValues target_values, sdv::someip::SomeIPConfig _config) {
    uint16_t serviceID = 0;
    uint16_t instanceID = 0;
    uint16_t methodID = 0;
    uint8_t vss_payload[SOMEIP_METHOD_PAYLOAD_SIZE];
    memset(vss_payload,0x00,SOMEIP_METHOD_PAYLOAD_SIZE);
    for (const auto& mapping : _config.VSSMap)
    {
        if(mapping.metaData.serviceType.compare("Method") == 0)
        {
            serviceID = mapping.metaData.serviceID;
            instanceID = mapping.metaData.instanceID;
            methodID = mapping.metaData.methodID;
            for (const auto& node : mapping.vssNodes)
            {
                LOG_INFO<< "Name: " << node.name << ",Data type " <<node.datatype <<", Byte Offset: " << node.byteOffset << ", Length: " << (unsigned)node.length << std::endl;
                sdv::databroker::v1::DataType type = getDataType(node.datatype);
                if (target_values.find(node.name) != target_values.end())
                {
                    methodID = node.methodId;
                    auto data = target_values.at(node.name);
                    if ((node.length > 0) && (node.byteOffset >= 0))
                    {
                        /* Check for any transform node */
                        if (node.transformMapping.size() > 0)
                        {
                            auto it = node.transformMapping.find(std::to_string(data.bool_()));
                            if (it != node.transformMapping.end())
                            {
                                copyJsonValueType(&vss_payload[node.byteOffset], it->second, node.length);
                            }
                        } 
                        else 
                        {
                            switch (type)
                            {
                                case sdv::databroker::v1::DataType::BOOL:
                                    {
                                        vss_payload[node.byteOffset] = data.bool_();
                                        break;
                                    }
                                case sdv::databroker::v1::DataType::UINT8:
                                    {
                                        vss_payload[node.byteOffset] = static_cast<uint8_t>(data.uint32());
                                        break;
                                    }
                                case sdv::databroker::v1::DataType::INT8:
                                    {
                                        vss_payload[node.byteOffset] = static_cast<int8_t>(data.int32());
                                        break;
                                    }
                                case sdv::databroker::v1::DataType::UINT8_ARRAY:
                                    {
                                        if (data.has_uint32_array())
                                        {
                                            //LOG_INFO<< "has_uint32_array: " <<data.uint32_array().values(0)<< std::endl;
                                            for (size_t i = 0; i < node.length; i++)
                                            {
                                                vss_payload[node.byteOffset + i] = data.uint32_array().values(i);
                                            }
                                            if (node.length == 4)
                                            {
                                                //allign 16 bit client ID to last byte of uint16 for Lighting app
                                                vss_payload[3] = vss_payload[2];
                                                vss_payload[2] = 0;
                                            }
                                        }
                                    }
                                    break;
                                case sdv::databroker::v1::DataType::UINT16:
                                    {
                                        auto uint16_value = static_cast<uint16_t>(data.uint32());
                                        std::memcpy(&vss_payload[node.byteOffset], &uint16_value, node.length);
                                    }
                                    break;
                                case sdv::databroker::v1::DataType::UINT16_ARRAY:
                                    {
                                        if (data.has_uint32_array())
                                        {
                                            /* Customized for payload [uint8][uint16] Payload */
                                            vss_payload[node.byteOffset] = static_cast<uint8_t>(data.uint32_array().values(0));
                                            auto uint16_value = data.uint32_array().values(1);
                                            uint16_value = (uint16_value >> 8) | (uint16_value << 8);
                                            std::memcpy(&vss_payload[node.byteOffset + 1], &uint16_value, 2);
                                        }
                                    }
                                    break;
                                case sdv::databroker::v1::DataType::INT16:
                                    {
                                        auto int16_value = static_cast<int16_t>(data.int32());
                                        std::memcpy(&vss_payload[node.byteOffset], &int16_value, node.length);
                                    }
                                    break;                                    
                                case sdv::databroker::v1::DataType::INT16_ARRAY:
                                    {
                                        if (data.has_int32_array())
                                        {
                                            /* Customized for driving Control Data [int16][uint16] Payload */
                                            auto uint16_value = static_cast<uint16_t>(data.int32_array().values(0));
                                            uint16_value = (uint16_value >> 8) | (uint16_value << 8);
                                            std::memcpy(&vss_payload[node.byteOffset], &uint16_value, 2);
                                            uint16_value = static_cast<uint16_t>(data.int32_array().values(1));
                                            uint16_value = (uint16_value >> 8) | (uint16_value << 8);
                                            std::memcpy(&vss_payload[node.byteOffset + 2], &uint16_value, 2);
                                        }
                                    }
                                    break;
                                case sdv::databroker::v1::DataType::TIMESTAMP_ARRAY: /* Workaround since we cant add custom data type */
                                    {
                                        if (data.has_int32_array())
                                        {
                                            /* Customized for driving Control Data [int8][uint16] Payload */
                                            vss_payload[node.byteOffset] = static_cast<int8_t>(data.int32_array().values(0));
                                            auto uint16_value = static_cast<uint16_t>(data.int32_array().values(1));
                                            uint16_value = (uint16_value >> 8) | (uint16_value << 8);
                                            std::memcpy(&vss_payload[node.byteOffset + 1], &uint16_value, 2);
                                        }
                                    }
                                    break;                                                                    
                                case sdv::databroker::v1::DataType::UINT32:
                                    {
                                        auto uint32_value = data.uint32();
                                        std::memcpy(&vss_payload[node.byteOffset], &uint32_value, node.length);
                                    }
                                    break;
                                case sdv::databroker::v1::DataType::FLOAT:
                                    {
                                        sdv::someip::wiper::float_to_bytes(data.float_(), &vss_payload[node.byteOffset]);
                                    }
                                    break;
                                case sdv::databroker::v1::DataType::STRING:
                                    {
                                        std::memcpy(&vss_payload[node.byteOffset], &data.string(), node.length);
                                    }
                                    break;
                                default:
                                    std::cout << "Unsupported data type." << std::endl;
                                    break;
                            }
                        }

                    }
                    // Send SOME/IP request
                    if ((someip_client_) && (serviceID != 0) && (instanceID != 0) && (methodID != 0)) 
                    {
                        std::vector<vsomeip::byte_t> payload;
                        payload.insert(payload.end(), &vss_payload[0], &vss_payload[sizeof(vss_payload)]);
                        someip_client_->SendRequest(
                                serviceID,
                                instanceID,
                                methodID,
                                payload);
                    }

                }
                else
                {
                    LOG_INFO<< "Name: "<< node.name << " no set request received" << std::endl; 
                }

            }
        }
    }
        

}

void SomeipFeederAdapter::Start() {
    LOG_INFO << "Starting adapter..." << std::endl;
    if (databroker_feeder_) {
        // start databropker feeder thread
        feeder_thread_ = std::make_shared<std::thread> (&sdv::broker_feeder::DataBrokerFeeder::Run, databroker_feeder_);
        int rc = pthread_setname_np(feeder_thread_->native_handle(), "broker_feeder");
        if (rc != 0) {
            LOG_ERROR << "Failed setting datafeeder thread name:" << rc << std::endl;
        }
    }
    if (actuator_subscriber_) {
        std::this_thread::sleep_for(std::chrono::milliseconds(50));
        // start target actuator subscription
        subscriber_thread_ = std::make_shared<std::thread> (
            &sdv::broker_feeder::kuksa::ActuatorSubscriber::Run, actuator_subscriber_);
        int rc = pthread_setname_np(subscriber_thread_->native_handle(), "target_subscr");
        if (rc != 0) {
            LOG_ERROR << "Failed setting someip thread name:" << rc << std::endl;
        }
    }
    if (someip_active_ && someip_client_) {
        std::this_thread::sleep_for(std::chrono::milliseconds(50));
        // start vsomeip app "main" thread
        someip_thread_ = std::make_shared<std::thread> (&sdv::someip::SomeIPClient::Run, someip_client_);
        int rc = pthread_setname_np(someip_thread_->native_handle(), "someip_main");
        if (rc != 0) {
            LOG_ERROR << "Failed setting someip thread name:" << rc << std::endl;
        }
    }
    feeder_active_ = true;
}

void SomeipFeederAdapter::Shutdown() {
    std::lock_guard<std::mutex> its_lock(shutdown_mutex_);
    LOG_DEBUG << "feeder_active_=" << feeder_active_
            << ", shutdown_requested_=" << shutdown_requested_<< std::endl;
    if (shutdown_requested_) {
        return;
    }
    shutdown_requested_ = true;
    feeder_active_ = false;

    if (subscriber_thread_ && actuator_subscriber_) {
        LOG_INFO << "Stopping actuator subscriber..." << std::endl;
        actuator_subscriber_->Shutdown();
    }
    if (feeder_thread_ && databroker_feeder_) {
        LOG_INFO << "Stopping databroker feeder..." << std::endl;
        databroker_feeder_->Shutdown();
    }
    if (someip_client_) {
        LOG_INFO << "Stopping someip client..." << std::endl;
        someip_client_->Shutdown();
        if (someip_thread_ && someip_thread_->joinable()) {
            if (someip_thread_->get_id() != std::this_thread::get_id()) {
                LOG_TRACE << "Joining someip thread..." << std::endl;
                someip_thread_->join();
                LOG_TRACE << "someip thread joined." << std::endl;
            } else {
                LOG_ERROR << "WARNING! Skipped joining someip from the same thread..." << std::endl;
                someip_thread_->detach();
            }
        }
    }
    // join feeder after stopping someip
    if (feeder_thread_ && feeder_thread_->joinable()) {
        LOG_TRACE << "Joining datafeeder thread..." << std::endl;
        feeder_thread_->join();
        LOG_TRACE << "datafeeder thread joined." << std::endl;
    }

    if (subscriber_thread_ && subscriber_thread_->joinable()) {
        LOG_TRACE << "Joining subscriber thread..." << std::endl;
        subscriber_thread_->join();
        LOG_TRACE << "subscriber thread joined." << std::endl;
    }
    LOG_TRACE << "done." << std::endl;
}

void SomeipFeederAdapter::FeedDummyData() {
    auto vss = WIPER_VSS_PATH + ".ActualPosition";
    auto vss_target = WIPER_VSS_PATH + ".ActualPosition";
    float target_pos = 110;

    if (!databroker_feeder_) {
        return;
    }
    LOG_INFO << "Starting dummy feeder" << std::endl;
    for (float pos=0.0; feeder_active_ && pos<target_pos; pos += 3.14) {
        { // feed ActualPosition
            LOG_INFO << "Feed Value " << pos << " to '" << vss << "'" << std::endl;
            sdv::databroker::v1::Datapoint datapoint;
            datapoint.set_float_value(pos);
            if (!datapoint.has_timestamp()) {
                auto ts = datapoint.mutable_timestamp();
                struct timespec tv;
                int rc = clock_gettime(CLOCK_REALTIME, &tv);
                if (rc == 0) {
                    ts->set_seconds(tv.tv_sec);
                    ts->set_nanos(tv.tv_nsec);
                }
            }
            databroker_feeder_->FeedValue(vss, datapoint);
        }
        { // feed TargetPosition
            LOG_INFO << "Feed Value " << target_pos << " to '" << vss_target << "'" << std::endl;
            sdv::databroker::v1::Datapoint datapoint;
            datapoint.set_float_value(target_pos);
            databroker_feeder_->FeedValue(vss_target, datapoint);
        }

        std::this_thread::sleep_for(std::chrono::milliseconds(1000));
    }
}

std::string bytes_to_ascii_string(const uint8_t* payload, size_t payload_size) {
    return std::string(reinterpret_cast<const char*>(payload), payload_size);
}

int SomeipFeederAdapter::on_someip_message(
            vsomeip::service_t service_id, vsomeip::instance_t instance_id, vsomeip::method_t method_id,
            const uint8_t *payload, size_t payload_length)
{
    LOG_INFO << "on_someip_message Service ID : "<<service_id <<" Inst ID : "<< instance_id <<" Method ID : "<< method_id << std::endl;
    sdv::databroker::v1::Datapoint value;
    for (const auto& mapping : someip_client_->GetConfig().VSSMap)
    {
        LOG_INFO<<"JSON Config Service ID " <<std::hex << mapping.metaData.serviceID <<std::endl;
        LOG_INFO<<"JSON Config VSS Node Info "<<mapping.vssNodes.size() <<std::endl;
        if(mapping.metaData.serviceType.compare("Event") == 0 &&
           service_id == someip_client_->GetConfig().service &&
           instance_id == someip_client_->GetConfig().instance )
        {
            for (const auto& node : mapping.vssNodes)
            {      
                LOG_INFO << "on_someip_message Service Vss Node Event ID : " << node.methodId;
                if (node.methodId == method_id)
                {
                    if ((node.length > 0) && (node.byteOffset >= 0))
                    {
                        sdv::databroker::v1::DataType type = getDataType(node.datatype);
                        auto tmpValue = 0;
                        float f_value = 0;
                        uint32_t unsignedintvalue = 0;
                        bool feed_value = false;

                        switch (type)
                        {
                            case sdv::databroker::v1::DataType::BOOL:
                                tmpValue = payload[node.byteOffset];
                                value = sdv::broker_feeder::createDatapoint(static_cast<bool>(tmpValue));
                                feed_value = true;
                                break;
                            case sdv::databroker::v1::DataType::UINT8:
                                tmpValue = payload[node.byteOffset];
                                value = sdv::broker_feeder::createDatapoint(static_cast<uint32_t>(tmpValue));
                                feed_value = true;
                                break;
                            case sdv::databroker::v1::DataType::UINT16:
                                // Correct byte order
                                tmpValue = (static_cast<uint16_t>(payload[node.byteOffset + 1]) | (static_cast<uint16_t>(payload[node.byteOffset]) << 8));
                                value = sdv::broker_feeder::createDatapoint(static_cast<uint32_t>(tmpValue));
                                feed_value = true;
                                break;            
                            case sdv::databroker::v1::DataType::INT16:
                                // Correct byte order
                                tmpValue = static_cast<int16_t>((static_cast<uint16_t>(payload[node.byteOffset + 1]) | (static_cast<uint16_t>(payload[node.byteOffset]) << 8)));
                                value = sdv::broker_feeder::createDatapoint(static_cast<int32_t>(tmpValue));
                                feed_value = true;
                                break;                                                    
                            case sdv::databroker::v1::DataType::INT8:
                                tmpValue = static_cast<int8_t>(payload[node.byteOffset]);
                                value = sdv::broker_feeder::createDatapoint(static_cast<int32_t>(tmpValue));
                                feed_value = true;
                                break;                                
                            case sdv::databroker::v1::DataType::UINT32:
                                memcpy(&unsignedintvalue,&payload[node.byteOffset], 4);
                                tmpValue = unsignedintvalue;
                                value = sdv::broker_feeder::createDatapoint(static_cast<uint32_t>(tmpValue));
                                feed_value = true;
                                break;
                            case sdv::databroker::v1::DataType::FLOAT:
                                sdv::someip::wiper::bytes_to_float(&payload[node.byteOffset], &f_value);
                                tmpValue = static_cast<float>(f_value);
                                value = sdv::broker_feeder::createDatapoint(static_cast<float>(f_value));
                                feed_value = true;
                                break;
                            case sdv::databroker::v1::DataType::STRING:
                            {
                                std::string msg = bytes_to_ascii_string(&payload[node.byteOffset],node.length);
                                value = sdv::broker_feeder::createDatapoint(msg);
                                feed_value = true;
                                break;
                            }
                            default:
                                LOG_INFO << "Unsupported data type." << std::endl;
                                break;
                        }
                        
                        /* Check for any transform node */
                        if (node.transformMapping.size() > 0)
                        {
                            LOG_INFO << "VSS Name : " <<node.name <<" Transform from " << tmpValue <<std::endl;
                            for (const auto& list : node.transformMapping)
                            {
                                LOG_INFO << list.first << " mapped " << list.second<< std::endl;
                            }
                            auto it = node.transformMapping.find(std::to_string(tmpValue));
                            if (it != node.transformMapping.end())
                            {
                                LOG_INFO << "Conversion as per transform mapping :" << it->second<<std::endl;
                                value = sdv::broker_feeder::createDatapoint(it->second);
                                feed_value = true;
                            }
                            else
                            {
                                feed_value = false;
                                LOG_INFO << "Data transform value not found in mapping" << std::endl;
                            }
                        }
                        if(feed_value)
                        {
                            databroker_feeder_->FeedValue(node.name,value);
                            LOG_INFO << "Feed VSS Name : " <<node.name<< " value = " << tmpValue <<std::endl;
                            LOG_INFO << "Feed VSS Value Case :" <<value.value_case()<<std::endl;
                        }

                    }
                }
            }

        }

    }
    return 0;
}

void SomeipFeederAdapter::copyJsonValueType(uint8_t* payload, const Json::Value value, size_t size)
{
    if (value.isBool()) 
    {
        bool boolValue = value.asBool();
        std::memcpy(payload, &boolValue, size);
    }
    else if (value.isString())
    {
        std::string stringValue = value.asString();
        std::memcpy(payload, stringValue.c_str(), size);
    }
    else if (value.isNumeric())
    {
        if (value.isInt())
        {
            int intValue = value.asInt();
            std::memcpy(payload, &intValue, size);

        }
        else if (value.isUInt())
        {
            unsigned int uintValue = value.asUInt();
            std::memcpy(payload, &uintValue, size);

        }
        else if (value.isInt64())
        {
            int64_t int64Value = value.asInt64();
            std::memcpy(payload, &int64Value, size);

        }
        else if (value.isUInt64())
        {
            uint64_t uint64Value = value.asUInt64();
            std::memcpy(payload, &uint64Value, size);

        }
        else if (value.isDouble())
        {
            double doubleValue = value.asDouble();
            std::memcpy(payload, &doubleValue, size);
        }
    }
    else
    {
        std::ostringstream oss;
        Json::StreamWriterBuilder builder;
        std::unique_ptr<Json::StreamWriter> writer(builder.newStreamWriter());
        writer->write(value, &oss);
        std::string serializedJson = oss.str();

        if (serializedJson.length() > size) 
        {
            LOG_ERROR << "Error: Array size is too small to hold the serialized JSON data." << std::endl;
        }
        else
        {
            std::memcpy(payload, serializedJson.c_str(), serializedJson.length());
        }
    }
}

}  // namespace adapter
}  // namespace sdv
