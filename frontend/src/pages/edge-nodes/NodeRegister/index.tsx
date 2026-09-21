import { useState } from 'react'
import { Steps, Form, Input, Select, InputNumber, Slider, Button, Alert, Upload, Checkbox, Result, Descriptions, message, Card, Space, Layout } from 'antd'
import { Upload as UploadIcon } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import type { UploadProps } from 'antd'

import type { RegisterFormData } from '@/types/edgeNode'

const { Option } = Select
const { TextArea } = Input
const { Content } = Layout

const NodeRegister: React.FC = () => {
  const navigate = useNavigate()
  const [currentStep, setCurrentStep] = useState(0)
  const [form] = Form.useForm<RegisterFormData>()
  const [loading, setLoading] = useState(false)
  const [testConnectionLoading, setTestConnectionLoading] = useState(false)
  const [registrationResult, setRegistrationResult] = useState<any>(null)

  const steps = [
    { title: '基本信息', description: '填写节点基本信息' },
    { title: '网络配置', description: '配置网络连接' },
    { title: '安全证书', description: '设置安全证书' },
    { title: '完成注册', description: '注册完成' }
  ]

  const validateIP = (_: any, value: string) => {
    const ipRegex = /^(\d{1,3}\.){3}\d{1,3}$/
    if (!value || !ipRegex.test(value)) {
      return Promise.reject('请输入有效的IP地址')
    }
    const parts = value.split('.')
    if (parts.some(part => parseInt(part) > 255)) {
      return Promise.reject('IP地址段不能大于255')
    }
    return Promise.resolve()
  }

  const validatePort = (_: any, value: number) => {
    if (!value || value < 1024 || value > 65535) {
      return Promise.reject('端口号范围：1024-65535')
    }
    return Promise.resolve()
  }

  const testConnection = async () => {
    const values = form.getFieldsValue()
    if (!values.ipAddress || !values.port) {
      message.error('请先填写IP地址和端口号')
      return
    }

    setTestConnectionLoading(true)
    try {
      await new Promise(resolve => setTimeout(resolve, 2000))
      message.success('连接测试成功，延迟: 45ms')
    } catch (error) {
      message.error('连接测试失败')
    } finally {
      setTestConnectionLoading(false)
    }
  }

  const next = async () => {
    try {
      if (currentStep === 0) {
        await form.validateFields(['nodeName', 'nodeType', 'location'])
      } else if (currentStep === 1) {
        await form.validateFields(['ipAddress', 'port'])
      } else if (currentStep === 2) {
        const values = form.getFieldsValue()
        if (values.certificateType === 'upload') {
          await form.validateFields(['certificate', 'privateKey'])
        }
        await form.validateFields(['agreeToTerms'])
      }

      setCurrentStep(currentStep + 1)
    } catch (error) {
      // Validation failed
    }
  }

  const prev = () => {
    setCurrentStep(currentStep - 1)
  }

  const handleSubmit = async () => {
    setLoading(true)
    try {
      const values = form.getFieldsValue()
      await new Promise(resolve => setTimeout(resolve, 2000))

      const result = {
        nodeId: 'NODE-2026-001',
        configFile: 'https://cdn.example.com/node-config.json',
        message: '注册成功',
        nodeName: values.nodeName,
        accessAddress: `${values.ipAddress}:${values.port}`,
        certificateExpiry: '2026-02-04 至 2027-02-04'
      }

      setRegistrationResult(result)
      setCurrentStep(3)
      message.success('节点注册成功！')
    } catch (error) {
      message.error('注册失败，请重试')
    } finally {
      setLoading(false)
    }
  }

  const uploadProps: UploadProps = {
    beforeUpload: (file) => {
      const isValidType = file.type === 'application/x-x509-ca-cert' || file.name.endsWith('.crt') || file.name.endsWith('.key')
      if (!isValidType) {
        message.error('只支持.crt或.key文件')
        return false
      }
      const isLt2M = file.size / 1024 / 1024 < 2
      if (!isLt2M) {
        message.error('文件大小不能超过2MB')
        return false
      }
      return false
    }
  }

  const renderStepContent = () => {
    switch (currentStep) {
      case 0:
        return (
          <Form form={form} layout="vertical">
            <Form.Item
              name="nodeName"
              label="节点名称"
              rules={[{ required: true, message: '请输入节点名称' }, { min: 2, max: 50, message: '节点名称长度2-50字符' }]}
            >
              <Input placeholder="例如：北京数据中心-节点01" />
            </Form.Item>

            <Form.Item
              name="nodeType"
              label="节点类型"
              rules={[{ required: true, message: '请选择节点类型' }]}
            >
              <Select placeholder="选择节点类型">
                <Option value="training">训练节点</Option>
                <Option value="validation">验证节点</Option>
                <Option value="hybrid">混合节点</Option>
              </Select>
            </Form.Item>

            <Form.Item label="地理位置">
              <Input.Group compact>
                <Form.Item name={['location', 'province']} noStyle rules={[{ required: true, message: '请选择省份' }]}>
                  <Select placeholder="省份" style={{ width: '33%' }}>
                    <Option value="北京市">北京市</Option>
                    <Option value="上海市">上海市</Option>
                    <Option value="广东省">广东省</Option>
                  </Select>
                </Form.Item>
                <Form.Item name={['location', 'city']} noStyle rules={[{ required: true, message: '请选择城市' }]}>
                  <Select placeholder="城市" style={{ width: '33%' }}>
                    <Option value="海淀区">海淀区</Option>
                    <Option value="浦东新区">浦东新区</Option>
                    <Option value="天河区">天河区</Option>
                  </Select>
                </Form.Item>
                <Form.Item name={['location', 'district']} noStyle>
                  <Input placeholder="区/街道" style={{ width: '34%' }} />
                </Form.Item>
              </Input.Group>
            </Form.Item>

            <Form.Item name="description" label="节点描述">
              <TextArea
                placeholder="描述节点的硬件配置、数据类型等"
                rows={3}
                maxLength={200}
                showCount
              />
            </Form.Item>
          </Form>
        )

      case 1:
        return (
          <Form form={form} layout="vertical">
            <Form.Item
              name="ipAddress"
              label="IP地址"
              rules={[{ required: true, validator: validateIP }]}
            >
              <Input placeholder="192.168.1.100" />
            </Form.Item>

            <Form.Item
              name="port"
              label="端口号"
              rules={[{ required: true, validator: validatePort }]}
              initialValue={8080}
            >
              <InputNumber min={1024} max={65535} style={{ width: '100%' }} />
            </Form.Item>

            <Form.Item name="publicIp" label="公网IP">
              <Input placeholder="如果有公网IP请填写" />
            </Form.Item>

            <Form.Item name="bandwidth" label="带宽" initialValue={100}>
              <Slider
                min={10}
                max={1000}
                marks={{ 10: '10', 100: '100', 500: '500', 1000: '1000' }}
                tooltip={{ formatter: (value: number | undefined) => `${value} Mbps` }}
              />
            </Form.Item>

            <Alert
              message="网络连通性测试"
              description="注册前将进行网络连通性测试，确保节点可访问"
              type="info"
              showIcon
              className="mb-4"
            />

            <Button
              type="default"
              onClick={testConnection}
              loading={testConnectionLoading}
              className="mb-4"
            >
              测试连接
            </Button>
          </Form>
        )

      case 2:
        return (
          <Form form={form} layout="vertical">
            <Form.Item
              name="certificateType"
              label="证书类型"
              rules={[{ required: true, message: '请选择证书类型' }]}
              initialValue="auto"
            >
              <Select>
                <Option value="auto">使用平台自动生成证书（推荐）</Option>
                <Option value="upload">上传自有证书</Option>
              </Select>
            </Form.Item>

            <Form.Item
              noStyle
              shouldUpdate={(prevValues, currentValues) => prevValues.certificateType !== currentValues.certificateType}
            >
              {({ getFieldValue }) =>
                getFieldValue('certificateType') === 'upload' ? (
                  <>
                    <Form.Item
                      name="certificate"
                      label="证书文件"
                      rules={[{ required: true, message: '请上传证书文件' }]}
                    >
                      <Upload {...uploadProps} accept=".crt">
                        <Button icon={<UploadIcon className="w-4 h-4" />}>选择证书文件</Button>
                      </Upload>
                    </Form.Item>

                    <Form.Item
                      name="privateKey"
                      label="私钥文件"
                      rules={[{ required: true, message: '请上传私钥文件' }]}
                    >
                      <Upload {...uploadProps} accept=".key">
                        <Button icon={<UploadIcon className="w-4 h-4" />}>选择私钥文件</Button>
                      </Upload>
                    </Form.Item>
                  </>
                ) : null
              }
            </Form.Item>

            <Form.Item
              name="agreeToTerms"
              valuePropName="checked"
              rules={[{ required: true, message: '请同意服务协议' }]}
            >
              <Checkbox>我同意《节点服务协议》</Checkbox>
            </Form.Item>

            <Alert
              message="安全提醒"
              description="为保证数据传输安全，需要上传TLS证书。如果没有证书，可以使用平台自动生成的证书"
              type="warning"
              showIcon
            />
          </Form>
        )

      case 3:
        return registrationResult ? (
          <Result
            status="success"
            title="节点注册成功！"
            subTitle={`节点ID: ${registrationResult.nodeId}`}
            extra={[
              <Button key="download" type="primary">
                下载配置文件
              </Button>,
              <Button key="list" onClick={() => navigate('/app/edge-nodes')}>
                查看节点列表
              </Button>
            ]}
          >
            <Descriptions bordered column={1}>
              <Descriptions.Item label="节点名称">{registrationResult.nodeName}</Descriptions.Item>
              <Descriptions.Item label="访问地址">{registrationResult.accessAddress}</Descriptions.Item>
              <Descriptions.Item label="证书有效期">{registrationResult.certificateExpiry}</Descriptions.Item>
            </Descriptions>

            <Alert
              message="下一步"
              description="请下载节点配置文件，并在您的服务器上启动节点程序。详细教程请参考文档。"
              type="info"
              showIcon
              className="mt-4"
            />
          </Result>
        ) : null

      default:
        return null
    }
  }

  return (
    <Content className="p-6 bg-gray-50 min-h-screen">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold m-0">节点注册</h1>
      </div>

      <Card bordered={false} className="shadow-sm mb-4">
        <Steps current={currentStep} items={steps} />
      </Card>

      <Card bordered={false} className="shadow-sm">
        {renderStepContent()}

        {currentStep < 3 && (
          <div className="mt-6 text-right">
            <Space>
              {currentStep > 0 && (
                <Button onClick={prev}>
                  上一步
                </Button>
              )}
              {currentStep < 2 && (
                <Button type="primary" onClick={next}>
                  下一步
                </Button>
              )}
              {currentStep === 2 && (
                <Button type="primary" loading={loading} onClick={handleSubmit}>
                  提交注册
                </Button>
              )}
            </Space>
          </div>
        )}
      </Card>
    </Content>
  )
}

export default NodeRegister
