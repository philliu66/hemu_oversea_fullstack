import { StepsForm } from '@ant-design/pro-components';
import { useIntl } from '@umijs/max';
import { App, Button, Drawer, Space } from 'antd';
import React, { useEffect, useRef, useState } from 'react';
import { addMissionFissionData } from '@/services/admin/missions';
import type { DhProductDetailPublic, DhProductPublic } from '@/types/api';
import { diffAttrList } from './attrDiff';
import { FissionProductStep } from './FissionProductStep';
import { SeedProductSelectTable } from './SeedProductSelectTable';

const TRACKED_KEYS = [
  'item_name',
  'key_word1',
  'key_word2',
  'key_word3',
  'cate_pub_id',
  'item_group_id',
  'store_id',
  'attr_list',
  'sku_list',
  'item_img_list',
  'item_spec_self_def_list',
  'html_content',
  'short_desc',
  'after_sale_template_id',
  'shipping_model_id',
] as const satisfies readonly (keyof DhProductDetailPublic)[];

function buildUpdateData(
  baseline: DhProductDetailPublic,
  current: DhProductDetailPublic,
): Record<string, unknown> {
  const update: Record<string, unknown> = {};
  for (const key of TRACKED_KEYS) {
    if (key === 'attr_list') {
      const attrDiff = diffAttrList(baseline.attr_list, current.attr_list);
      if (attrDiff) {
        update.attr_list = attrDiff;
      }
      continue;
    }
    const before = JSON.stringify(baseline[key] ?? null);
    const after = JSON.stringify(current[key] ?? null);
    if (before !== after) {
      update[key] = current[key] ?? null;
    }
  }
  return update;
}

export function AddFissionDrawer({
  open,
  missionId,
  onClose,
  onAdded,
}: {
  open: boolean;
  missionId: number;
  onClose: () => void;
  onAdded: () => void;
}) {
  const intl = useIntl();
  const { message } = App.useApp();
  const [selected, setSelected] = useState<DhProductPublic>();
  const [step, setStep] = useState(0);
  const [submitting, setSubmitting] = useState(false);
  const baselineRef = useRef<DhProductDetailPublic | null>(null);
  const currentRef = useRef<DhProductDetailPublic | null>(null);

  const resetEditor = () => {
    baselineRef.current = null;
    currentRef.current = null;
  };

  const resetDrawer = () => {
    setSelected(undefined);
    setStep(0);
    resetEditor();
  };

  useEffect(() => {
    if (!open) {
      resetDrawer();
    }
  }, [open]);

  const handleSelect = (product: DhProductPublic) => {
    setSelected((prev) => {
      if (prev?.id !== product.id) {
        resetEditor();
      }
      return product;
    });
    setStep(1);
  };

  const handleDetailChange = (detail: DhProductDetailPublic) => {
    if (baselineRef.current == null || detail.id !== selected?.id) {
      baselineRef.current = structuredClone(detail);
    }
    currentRef.current = detail;
  };

  const handleConfirm = async () => {
    if (!selected) {
      message.warning(
        intl.formatMessage({
          id: 'pages.mission.add.selectRequired',
          defaultMessage: '请先选择一个种子商品',
        }),
      );
      return false;
    }
    const baseline = baselineRef.current;
    const current = currentRef.current;
    if (!baseline || !current || current.id !== selected.id) {
      message.warning(
        intl.formatMessage({
          id: 'pages.mission.add.detailNotReady',
          defaultMessage: '商品信息还在加载，请稍后再确认',
        }),
      );
      return false;
    }
    const updateJson = buildUpdateData(baseline, current);
    setSubmitting(true);
    try {
      await addMissionFissionData({
        mission_id: missionId,
        seed_product_id: selected.id,
        update_json: updateJson,
        raw_json: current,
      });
      message.success(
        intl.formatMessage({
          id: 'pages.mission.add.success',
          defaultMessage: '已加入任务',
        }),
      );
      onAdded();
      return true;
    } catch {
      return false;
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Drawer
      title={intl.formatMessage({
        id: 'pages.mission.action.add',
        defaultMessage: '手动添加',
      })}
      open={open}
      width="80vw"
      destroyOnHidden
      onClose={() => {
        resetDrawer();
        onClose();
      }}
      styles={{
        body: {
          padding: 0,
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
        },
      }}
    >
      <div className="add-fission-shell">
        <style>{`
          .add-fission-shell {
            flex: 1;
            min-height: 0;
            display: flex;
            flex-direction: column;
          }
          .add-fission-shell > .ant-pro-steps-form {
            flex: 1;
            min-height: 0;
            display: flex;
            flex-direction: column;
          }
        `}</style>
        <StepsForm
          current={step}
          onCurrentChange={setStep}
          containerStyle={{
            width: '100%',
            maxWidth: '100%',
            minWidth: 0,
            margin: 0,
          }}
          stepsProps={{ size: 'small' }}
          submitter={{
            render: (props) => {
              if (props.step === 0) {
                return (
                  <Button type="primary" onClick={() => props.onSubmit?.()}>
                    {intl.formatMessage({
                      id: 'pages.mission.add.next',
                      defaultMessage: '下一步',
                    })}
                  </Button>
                );
              }
              return (
                <Space>
                  <Button onClick={() => props.onPre?.()}>
                    {intl.formatMessage({
                      id: 'pages.mission.add.prev',
                      defaultMessage: '上一步',
                    })}
                  </Button>
                  <Button
                    type="primary"
                    loading={submitting}
                    onClick={() => props.onSubmit?.()}
                  >
                    {intl.formatMessage({
                      id: 'pages.mission.add.confirm',
                      defaultMessage: '确认添加',
                    })}
                  </Button>
                </Space>
              );
            },
          }}
          layoutRender={({ stepsDom, formDom }) => (
            <div
              style={{
                flex: 1,
                minHeight: 0,
                display: 'flex',
                flexDirection: 'column',
              }}
            >
              <div
                style={{
                  flex: 'none',
                  position: 'sticky',
                  top: 0,
                  zIndex: 2,
                  padding: '16px 24px 12px',
                  background: 'var(--ant-color-bg-elevated, #fff)',
                  borderBottom:
                    '1px solid var(--ant-color-split, rgba(5,5,5,0.06))',
                }}
              >
                {stepsDom}
              </div>
              <div
                style={{ flex: 1, minHeight: 0, overflow: 'auto', padding: 24 }}
              >
                {formDom}
              </div>
            </div>
          )}
          stepsFormRender={(dom, submitter) => (
            <div
              style={{
                flex: 1,
                minHeight: 0,
                display: 'flex',
                flexDirection: 'column',
              }}
            >
              <div
                style={{
                  flex: 1,
                  minHeight: 0,
                  overflow: 'hidden',
                  display: 'flex',
                  flexDirection: 'column',
                }}
              >
                {dom}
              </div>
              <div
                style={{
                  flex: 'none',
                  textAlign: 'right',
                  padding: '12px 24px',
                  background: 'var(--ant-color-bg-elevated, #fff)',
                  borderTop:
                    '1px solid var(--ant-color-split, rgba(5,5,5,0.06))',
                }}
              >
                {submitter}
              </div>
            </div>
          )}
        >
          <StepsForm.StepForm
            title={intl.formatMessage({
              id: 'pages.mission.add.step.seed',
              defaultMessage: '选择种子商品',
            })}
            component={false}
            onFinish={async () => {
              if (!selected) {
                message.warning(
                  intl.formatMessage({
                    id: 'pages.mission.add.selectRequired',
                    defaultMessage: '请先选择一个种子商品',
                  }),
                );
                return false;
              }
              return true;
            }}
          >
            <div onSubmit={(event) => event.stopPropagation()}>
              <SeedProductSelectTable
                selectedId={selected?.id}
                onSelect={handleSelect}
              />
            </div>
          </StepsForm.StepForm>
          <StepsForm.StepForm
            title={intl.formatMessage({
              id: 'pages.mission.add.step.edit',
              defaultMessage: '修改商品数据',
            })}
            component={false}
            onFinish={handleConfirm}
          >
            {selected ? (
              <FissionProductStep
                key={selected.id}
                productId={selected.id}
                onDetailChange={handleDetailChange}
              />
            ) : null}
          </StepsForm.StepForm>
        </StepsForm>
      </div>
    </Drawer>
  );
}
