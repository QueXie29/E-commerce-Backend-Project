# 公开只读 ViewSet 响应 Mixin 拆分设计

## 背景

`CategoryViewSet` 和 `ProductViewSet` 继承 `ReadOnlyModelViewSet`，业务上只应提供列表与详情查询。但它们同时继承的 `ApiViewSetResponseMixin` 定义了 `create()`、`update()` 和 `destroy()`，DRF 路由器因此把公开路径错误地识别为支持写操作。

当前调用 `POST /api/categories/` 时，请求进入 `ApiViewSetResponseMixin.create()`。序列化校验完成后，该方法调用 `self.perform_create(serializer)`；而 `ReadOnlyModelViewSet` 不包含 `CreateModelMixin`，因此没有 `perform_create()`，最终返回 HTTP 500。

同样的问题也存在于公开商品 ViewSet，属于共享 Mixin 的职责边界错误。

## 目标

- 公开分类和商品 ViewSet 只暴露读取操作。
- `POST /api/categories/` 和 `POST /api/products/` 返回 HTTP 405，不进入创建逻辑，也不写入数据库。
- 管理端分类和商品 ViewSet 保持现有 CRUD 行为及统一响应结构。
- 普通用户访问管理端创建接口时，权限检查先于创建逻辑执行，返回 HTTP 403 和业务码 `40300`，数据库不产生记录。
- 不修改模型、序列化器、数据库结构和现有业务路由。

## 方案

将当前同时承担读写响应封装的 `ApiViewSetResponseMixin` 拆分为两个层次：

1. `ApiReadOnlyViewSetResponseMixin`
   - 只实现 `list()` 和 `retrieve()`。
   - 供 `CategoryViewSet` 和 `ProductViewSet` 使用。

2. `ApiModelViewSetResponseMixin`
   - 继承 `ApiReadOnlyViewSetResponseMixin`。
   - 实现 `create()`、`update()` 和 `destroy()`。
   - 供 `AdminCategoryViewSet` 和 `AdminProductViewSet` 使用。

公开 ViewSet 的方法集合将与 `ReadOnlyModelViewSet` 一致。DRF 路由器不会再为它们绑定 `create`、`update` 或 `destroy` action。管理端 ViewSet 仍继承 `ModelViewSet`，因此保留 `perform_create()`、`perform_update()` 和 `perform_destroy()` 扩展点。

## 请求流程

### 公开路径非法写请求

`POST /api/categories/` 的 URL 仍能匹配公开分类 ViewSet，但该 ViewSet 不再注册 POST action。DRF 返回 HTTP 405，请求不会执行序列化校验、`perform_create()` 或数据库保存。

`POST /api/products/` 使用相同流程。

### 管理端无权限写请求

普通用户调用 `POST /api/admin/categories/` 时，DRF 在分派到 `create()` 之前执行 `IsAdminRole.has_permission()`。权限拒绝由现有异常处理器转换为 HTTP 403、业务码 `40300`，不会进入创建逻辑。

### 管理端合法写请求

管理员调用管理端创建、更新或删除接口时，继续使用 `ApiModelViewSetResponseMixin` 的统一响应封装，并由 `ModelViewSet` 提供标准的 `perform_*` 扩展点。现有分类软删除和商品缓存清理逻辑保持不变。

## 错误处理

- 公开路径使用不支持的 HTTP 方法：HTTP 405。
- 普通用户访问管理端写接口：HTTP 403、业务码 `40300`。
- 管理端请求数据校验失败：继续交给现有 DRF 异常处理器处理。
- 本次不新增业务错误码，也不调整全局异常响应结构。

## 测试设计

在 `apps/products/tests.py` 增加回归测试，至少覆盖：

1. 普通用户 `POST /api/categories/` 返回 HTTP 405，分类数量不变。
2. 普通用户 `POST /api/products/` 返回 HTTP 405，商品数量不变。
3. 普通用户 `POST /api/admin/categories/` 返回 HTTP 403、业务码 `40300`，分类数量不变。
4. 管理员 `POST /api/admin/categories/` 返回 HTTP 201，并创建分类。
5. 现有管理员商品创建测试继续通过。

实施时先新增能够复现当前 HTTP 500 的测试并确认其按预期失败，再进行最小代码修改，最后运行产品应用测试和完整测试套件。

## 非目标

- 不允许通过公开路径创建或修改分类、商品。
- 不把公开路径的非法 POST 改成管理员备用写入口。
- 不修改管理员路由路径。
- 不处理与本问题无关的重构或文档改写。
